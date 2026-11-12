/*
  Talking skull - ESP32-S3 side (Waveshare ESP32-S3-DEV-KIT-N16R8)
  - LD2450 radar: detects visitors, sends PRESENCE 1 / PRESENCE 0 to the Mac over USB serial
  - Neck servo (HS-488HB, GPIO 5): turns toward the closest visitor using the radar's X/Y position
  - Jaw servo (HS-65MG, GPIO 4): follows "JAW n" (0 closed .. 255 open) sent by skull.py on the Mac
  - Eyes (two GC9A01 240x240): look at the visitor, blink, and react to LISTEN / THINK / SPEAK.
    They render on core 0 so they never hold up the jaw, neck or radar on core 1.

  Commands from the Mac (one per line):  JAW n | EYES 0/1 | STATE IDLE/LISTEN/THINK/SPEAK
  Handy from the Arduino Serial Monitor (115200):
    JAWUS 1500 | NECKUS 1500 | NECK -20 | TRACK      servo calibration
    EYES 1 | STATE THINK | BLINK | GAZE x y            eye testing (GAZE -100..100 each)

  Arduino IDE: board "ESP32S3 Dev Module", Flash 16MB, PSRAM "OPI PSRAM" (the eyes need it),
  USB CDC On Boot "Disabled". Libraries: "ESP32Servo" and "LovyanGFX" (Library Manager).
*/
#include <Arduino.h>
#include <ESP32Servo.h>
#define LGFX_USE_V1
#include <LovyanGFX.hpp>
#include "eye_art.h"      // original procedural eyes (tools/eyegen)

// ---------------- Wiring ----------------
const int JAW_PIN   = 4;
const int NECK_PIN  = 5;
const int RADAR_RX  = 16;   // ESP32 RX  <- LD2450 TX
const int RADAR_TX  = 17;   // ESP32 TX  -> LD2450 RX
// Eyes: both share SCL/SDA/DC/RST, each has its own CS
const int PIN_SCLK  = 12;
const int PIN_MOSI  = 11;
const int PIN_DC    = 8;
const int PIN_RST   = 18;
const int PIN_CS_L  = 10;
const int PIN_CS_R  = 9;
const uint32_t SPI_HZ = 20000000;   // 20 MHz worked on your jumper wires; try 40 MHz with short wires

// ---------------- Jaw calibration (microseconds) ----------------
// Find these with JAWUS commands in the Serial Monitor, then set them here.
const int JAW_CLOSED_US = 1400;
const int JAW_OPEN_US   = 2000;    // swap direction by making this smaller than CLOSED
const unsigned long JAW_TIMEOUT_MS = 400;   // close the jaw if the Mac goes quiet mid-word

// ---------------- Neck calibration ----------------
const int   NECK_CENTER_US  = 1500;
const float NECK_US_PER_DEG = 10.0;   // HS-488HB is roughly 10 us per degree
const float NECK_MAX_DEG    = 40.0;   // limit travel so it never hits the stops or snags wires
const bool  NECK_INVERT     = true;   // flip if the head turns AWAY from people
const float NECK_SMOOTH     = 0.08;   // 0..1 per 20 ms step; lower = slower, creepier
const float NECK_MAX_STEP   = 2.0;    // degrees per 20 ms step max

// ---------------- Eyes ----------------
const bool  EYE_INVERT_X  = false;    // flip if the eyes look AWAY from the visitor
const float EYE_DEG_RANGE = 30.0;     // degrees off-center that makes the eyes look all the way to the side
// Eye color and artwork come from eye_art_data.h. Regenerate it with tools/eyegen/eyegen.py.

// ---------------- Presence zone (mm, radar coordinates) ----------------
const int ZONE_MAX_Y = 2500;          // how far out counts as "at the skull"
const int ZONE_MAX_X = 1500;          // how wide (each side)
const unsigned long PRESENCE_ON_MS  = 400;   // must be seen this long before triggering
const unsigned long PRESENCE_OFF_MS = 4000;  // must be gone this long before "PRESENCE 0"

Servo jaw, neck;
HardwareSerial Radar(1);

// radar state
struct Target { int x, y; bool valid; };
Target targets[3];
unsigned long lastSeenMs = 0, firstSeenMs = 0;
bool presence = false;
float neckDeg = 0, neckGoalDeg = 0, targetDeg = 0;

// jaw / neck state
unsigned long lastJawMs = 0;
bool jawOpen = false;
bool manualNeck = false;

// ---------------- shared with the eye task (core 0) ----------------
enum SkullState { ST_IDLE, ST_LISTEN, ST_THINK, ST_SPEAK };
volatile bool  eyesOn = false;
volatile int   skullState = ST_IDLE;
volatile bool  hasTarget = false;
volatile float lookX = 0;               // -1..1, where the visitor is relative to where the head points
volatile bool  blinkRequest = false;
volatile bool  manualGaze = false;      // GAZE command overrides tracking for a few seconds
volatile float manualGx = 0, manualGy = 0;
volatile unsigned long manualGazeMs = 0;
volatile unsigned long eyeFrames = 0;

// ==================================================================
// Eye displays (from the Oct 28 bring-up sketch, with its fixes)
// ==================================================================
class LGFX : public lgfx::LGFX_Device {
  lgfx::Panel_GC9A01 _panel;
  lgfx::Bus_SPI      _bus;
public:
  LGFX() {
    {
      auto cfg = _bus.config();
      cfg.spi_host    = SPI2_HOST;
      cfg.spi_mode    = 0;
      cfg.freq_write  = SPI_HZ;
      cfg.freq_read   = 16000000;
      cfg.spi_3wire   = true;
      cfg.use_lock    = true;
      cfg.dma_channel = SPI_DMA_CH_AUTO;
      cfg.pin_sclk    = PIN_SCLK;
      cfg.pin_mosi    = PIN_MOSI;
      cfg.pin_miso    = -1;
      cfg.pin_dc      = PIN_DC;
      _bus.config(cfg);
      _panel.setBus(&_bus);
    }
    {
      auto cfg = _panel.config();
      cfg.pin_cs          = -1;      // manual CS
      cfg.pin_rst         = PIN_RST;
      cfg.pin_busy        = -1;
      cfg.panel_width     = 240;
      cfg.panel_height    = 240;
      cfg.offset_x        = 0;
      cfg.offset_y        = 0;
      cfg.offset_rotation = 0;
      cfg.readable        = false;
      cfg.invert          = true;
      cfg.rgb_order       = false;
      cfg.dlen_16bit      = false;
      cfg.bus_shared      = false;
      _panel.config(cfg);
    }
    setPanel(&_panel);
  }
};

LGFX tft;
LGFX_Sprite eye(&tft);

void deselect()          { digitalWrite(PIN_CS_L, HIGH); digitalWrite(PIN_CS_R, HIGH); }
void selectBoth()        { digitalWrite(PIN_CS_L, LOW);  digitalWrite(PIN_CS_R, LOW); }
void selectOnly(int cs)  {
  digitalWrite(PIN_CS_L, cs == PIN_CS_L ? LOW : HIGH);
  digitalWrite(PIN_CS_R, cs == PIN_CS_R ? LOW : HIGH);
}

// LovyanGFX skips re-sending the draw window if it hasn't changed. With two panels behind one
// driver that leaves the second panel ignoring frames, so force the window every time.
void forceWindow() { tft.setAddrWindow(0, 0, 1, 1); }

void pushEye(int cs) {
  tft.waitDMA();
  selectOnly(cs);
  tft.startWrite();
  forceWindow();
  eye.pushSprite(0, 0);
  tft.endWrite();
  tft.waitDMA();
  deselect();
}

void fillBoth(uint16_t color) {
  tft.waitDMA();
  selectBoth();
  tft.startWrite();
  forceWindow();
  tft.fillScreen(color);
  tft.endWrite();
  tft.waitDMA();
  deselect();
}

struct EyeAnim {
  float gx = 0, gy = 0, tx = 0, ty = 0;     // gaze current / target (-1..1)
  float pupil = 28, tPupil = 28;
  float lid = 0;                            // 0 open .. 1 closed
  float squint = 0, tSquint = 0;            // extra upper-lid droop
  bool  blinking = false;
  unsigned long blinkStart = 0, nextBlink = 0, nextSaccade = 0;
  float offX = 0, offY = 0;                 // saccade offset added to the tracking target
  int   lastState = -1;
} ea;

void renderEye() {
  eyeart::render((uint16_t*)eye.getBuffer(), ea.gx, ea.gy, ea.pupil - 6, ea.lid, ea.squint);
}

float frand(float lo, float hi) { return lo + (hi - lo) * (esp_random() % 10001) / 10000.0f; }

void startBlink(unsigned long now) { ea.blinking = true; ea.blinkStart = now; }

// Decide where to look and how to look, based on what the conversation is doing.
void updateEyeBehaviour(unsigned long now) {
  int s = skullState;
  if (s != ea.lastState) {                  // react to a state change
    ea.lastState = s;
    ea.nextSaccade = now;
    if (s == ST_THINK || s == ST_LISTEN) startBlink(now);
  }
  if (blinkRequest) { blinkRequest = false; startBlink(now); }

  // pupils and squint per state
  switch (s) {
    case ST_LISTEN: ea.tPupil = 34; ea.tSquint = 0.0f;  break;   // attentive, wide
    case ST_THINK:  ea.tPupil = 24; ea.tSquint = 0.35f; break;   // narrowed, scheming
    case ST_SPEAK:  ea.tPupil = 28; ea.tSquint = 0.15f; break;
    default:        ea.tPupil = 28; ea.tSquint = 0.1f;  break;
  }

  // saccades: little jumps around the main target, bigger "glances away" while thinking
  if (now >= ea.nextSaccade) {
    switch (s) {
      case ST_THINK:                         // look up and off to one side, like it's pondering
        ea.offX = (esp_random() & 1) ? frand(0.4f, 0.65f) : -frand(0.4f, 0.65f);
        ea.offY = -frand(0.35f, 0.55f);
        ea.nextSaccade = now + (unsigned long)frand(700, 1500);
        break;
      case ST_LISTEN:                        // steady on the visitor, tiny micro-saccades
        ea.offX = frand(-0.06f, 0.06f);
        ea.offY = frand(-0.05f, 0.05f);
        ea.nextSaccade = now + (unsigned long)frand(400, 1200);
        break;
      default:                               // speaking / greeting: mostly on them, occasional glance
        if (frand(0, 1) < 0.2f) { ea.offX = frand(-0.35f, 0.35f); ea.offY = frand(-0.2f, 0.15f); }
        else                    { ea.offX = frand(-0.1f, 0.1f);   ea.offY = frand(-0.08f, 0.08f); }
        ea.nextSaccade = now + (unsigned long)frand(500, 2000);
        break;
    }
  }

  // base target: the visitor (slightly downward, trick-or-treaters are short), else straight ahead
  float bx = hasTarget ? lookX : 0.0f;
  float by = hasTarget ? 0.15f : 0.0f;
  if (manualGaze) {
    if (now - manualGazeMs < 4000) { bx = manualGx; by = manualGy; ea.offX = ea.offY = 0; }
    else manualGaze = false;
  }
  ea.tx = constrain(bx + ea.offX, -1.0f, 1.0f);
  ea.ty = constrain(by + ea.offY, -1.0f, 1.0f);

  if (now >= ea.nextBlink) {
    startBlink(now);
    ea.nextBlink = now + (unsigned long)frand(2000, 6000);
  }
}

void eyeTask(void *) {
  bool blank = false;
  for (;;) {
    unsigned long now = millis();
    if (!eyesOn) {
      if (!blank) { fillBoth(TFT_BLACK); blank = true; }
      vTaskDelay(pdMS_TO_TICKS(30));
      continue;
    }
    if (blank) { blank = false; startBlink(now); }   // wake up with a blink

    updateEyeBehaviour(now);

    // snap toward the target (reads as a saccade), ease the rest
    ea.gx += (ea.tx - ea.gx) * 0.5f;
    ea.gy += (ea.ty - ea.gy) * 0.5f;
    ea.pupil  += (ea.tPupil - ea.pupil) * 0.15f;
    ea.squint += (ea.tSquint - ea.squint) * 0.15f;

    if (ea.blinking) {
      float t = (now - ea.blinkStart) / 160.0f;      // fast close, slower open
      if (t >= 1.0f) { ea.blinking = false; ea.lid = 0; }
      else ea.lid = (t < 0.4f) ? t / 0.4f : 1.0f - (t - 0.4f) / 0.6f;
    }

    renderEye();
    pushEye(PIN_CS_L);
    pushEye(PIN_CS_R);
    eyeFrames = eyeFrames + 1;
    vTaskDelay(1);
  }
}

void setupEyes() {
  pinMode(PIN_CS_L, OUTPUT);
  pinMode(PIN_CS_R, OUTPUT);
  selectBoth();                      // init and rotate both panels together
  tft.init();
  tft.setRotation(2);                // both panels are mounted so 180 degrees is upright
  tft.fillScreen(TFT_BLACK);
  tft.waitDMA();
  deselect();

  eye.setPsram(true);
  eye.setColorDepth(16);
  if (!eye.createSprite(240, 240)) {
    Serial.println("# ERROR: eye sprite allocation failed - set Tools > PSRAM to OPI PSRAM");
    return;
  }
  xTaskCreatePinnedToCore(eyeTask, "eyes", 8192, nullptr, 1, nullptr, 0);   // core 0
}

// ==================================================================
// Radar
// LD2450 frame: AA FF 03 00 | 3 x 8-byte targets | 55 CC   (30 bytes, 256000 baud)
// x, y, speed: bit 15 set = positive, clear = negative; low 15 bits = magnitude
// ==================================================================
int16_t ld2450Signed(uint8_t lo, uint8_t hi) {
  uint16_t raw = lo | (hi << 8);
  int16_t mag = raw & 0x7FFF;
  return (raw & 0x8000) ? mag : -mag;
}

bool readRadarFrame() {
  static uint8_t buf[30];
  static int pos = 0;
  static const uint8_t header[4] = {0xAA, 0xFF, 0x03, 0x00};
  bool got = false;
  while (Radar.available()) {
    uint8_t b = Radar.read();
    if (pos < 4) {
      if (b == header[pos]) buf[pos++] = b;
      else pos = (b == header[0]) ? (buf[0] = b, 1) : 0;
      continue;
    }
    buf[pos++] = b;
    if (pos == 30) {
      pos = 0;
      if (buf[28] != 0x55 || buf[29] != 0xCC) continue;
      for (int i = 0; i < 3; i++) {
        const uint8_t *t = &buf[4 + i * 8];
        targets[i].x = ld2450Signed(t[0], t[1]);
        targets[i].y = ld2450Signed(t[2], t[3]);
        targets[i].valid = !(t[0] == 0 && t[1] == 0 && t[2] == 0 && t[3] == 0) && targets[i].y > 0;
      }
      got = true;
    }
  }
  return got;
}

// closest target inside the zone, or -1
int closestTarget() {
  int best = -1; long bestD = 0;
  for (int i = 0; i < 3; i++) {
    if (!targets[i].valid) continue;
    if (targets[i].y > ZONE_MAX_Y || abs(targets[i].x) > ZONE_MAX_X) continue;
    long d = (long)targets[i].x * targets[i].x + (long)targets[i].y * targets[i].y;
    if (best < 0 || d < bestD) { best = i; bestD = d; }
  }
  return best;
}

// ==================================================================
// Servos
// ==================================================================
void setJaw(int value) {               // 0..255
  value = constrain(value, 0, 255);
  jaw.writeMicroseconds(map(value, 0, 255, JAW_CLOSED_US, JAW_OPEN_US));
  jawOpen = value > 0;
}

void writeNeck(float deg) {
  deg = constrain(deg, -NECK_MAX_DEG, NECK_MAX_DEG);
  if (NECK_INVERT) deg = -deg;
  neck.writeMicroseconds(NECK_CENTER_US + (int)(deg * NECK_US_PER_DEG));
}

// ==================================================================
// Commands from the Mac
// ==================================================================
void handleLine(String line) {
  line.trim();
  if (line.length() == 0) return;
  int sp = line.indexOf(' ');
  String cmd = (sp < 0 ? line : line.substring(0, sp));
  String arg = (sp < 0 ? "" : line.substring(sp + 1));
  cmd.toUpperCase();
  arg.toUpperCase();

  if (cmd == "JAW")         { setJaw(arg.toInt()); lastJawMs = millis(); }
  else if (cmd == "EYES")   { eyesOn = arg.toInt() != 0; }
  else if (cmd == "STATE") {
    if (arg == "LISTEN")     skullState = ST_LISTEN;
    else if (arg == "THINK") skullState = ST_THINK;
    else if (arg == "SPEAK") skullState = ST_SPEAK;
    else                     skullState = ST_IDLE;
  }
  else if (cmd == "BLINK")  { blinkRequest = true; }
  else if (cmd == "GAZE")   {
    int a = 0, b = 0;
    if (sscanf(arg.c_str(), "%d %d", &a, &b) == 2) {
      manualGx = constrain(a, -100, 100) / 100.0f;
      manualGy = constrain(b, -100, 100) / 100.0f;
      manualGazeMs = millis();
      manualGaze = true;
    }
  }
  else if (cmd == "JAWUS")  { jaw.writeMicroseconds(arg.toInt()); Serial.printf("# jaw %d us\n", arg.toInt()); }
  else if (cmd == "NECKUS") { manualNeck = true; neck.writeMicroseconds(arg.toInt()); Serial.printf("# neck %d us\n", arg.toInt()); }
  else if (cmd == "NECK")   { manualNeck = true; writeNeck(arg.toFloat()); }
  else if (cmd == "TRACK")  { manualNeck = false; }
  else Serial.printf("# unknown: %s\n", line.c_str());
}

void readMac() {
  static String line;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') { handleLine(line); line = ""; }
    else if (line.length() < 64) line += c;
  }
}

// ==================================================================
void setup() {
  Serial.begin(115200);
  Radar.setRxBufferSize(1024);
  Radar.begin(256000, SERIAL_8N1, RADAR_RX, RADAR_TX);

  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  jaw.setPeriodHertz(50);
  neck.setPeriodHertz(50);
  jaw.attach(JAW_PIN, 500, 2500);
  neck.attach(NECK_PIN, 500, 2500);
  setJaw(0);
  writeNeck(0);

  setupEyes();
  Serial.println("# skull esp32 ready");
}

void loop() {
  unsigned long now = millis();
  readMac();

  // radar -> presence, neck goal, eye target
  static unsigned long frames = 0, lastReportMs = 0;
  if (readRadarFrame()) {
    frames++;
    int t = closestTarget();
    if (t >= 0) {
      if (lastSeenMs == 0 || now - lastSeenMs > PRESENCE_OFF_MS) firstSeenMs = now;
      lastSeenMs = now;
      targetDeg = degrees(atan2((float)targets[t].x, (float)targets[t].y));
    }
  }
  bool seen = lastSeenMs && (now - lastSeenMs < PRESENCE_OFF_MS);
  if (!presence && seen && now - firstSeenMs >= PRESENCE_ON_MS) {
    presence = true;
    Serial.println("PRESENCE 1");
  } else if (presence && !seen) {
    presence = false;
    Serial.println("PRESENCE 0");
  }
  if (!seen) targetDeg = 0;              // nobody there: drift back to center
  neckGoalDeg = constrain(targetDeg, -NECK_MAX_DEG, NECK_MAX_DEG);

  // eyes look at the visitor relative to where the head is pointing now, so they lead the neck
  hasTarget = seen;
  float lx = constrain((targetDeg - neckDeg) / EYE_DEG_RANGE, -1.0f, 1.0f);
  lookX = EYE_INVERT_X ? -lx : lx;

  // status line every 2 s so you can see things are alive (lines starting with # are just info)
  if (now - lastReportMs >= 2000) {
    float secs = (now - lastReportMs) / 1000.0f;
    lastReportMs = now;
    if (frames == 0) {
      Serial.println("# radar: NO DATA - check LD2450 power and that RADAR_RX/RADAR_TX match your wiring (try swapping them)");
    } else {
      int t = closestTarget();
      int raw = -1;
      for (int i = 0; i < 3; i++) if (targets[i].valid) { raw = i; break; }
      if (t >= 0)        Serial.printf("# radar: %lu frames, IN ZONE x=%d y=%d mm\n", frames, targets[t].x, targets[t].y);
      else if (raw >= 0) Serial.printf("# radar: %lu frames, target OUTSIDE zone x=%d y=%d mm\n", frames, targets[raw].x, targets[raw].y);
      else               Serial.printf("# radar: %lu frames, nobody detected\n", frames);
    }
    frames = 0;
    if (eyesOn) Serial.printf("# eyes: %.1f fps\n", eyeFrames / secs);
    eyeFrames = 0;
    // repeat the current state so a Mac that connects late (or missed a line) still catches up
    Serial.println(presence ? "PRESENCE 1" : "PRESENCE 0");
  }

  // jaw safety: close if the Mac stopped sending
  if (jawOpen && now - lastJawMs > JAW_TIMEOUT_MS) setJaw(0);

  // smooth neck motion, every 20 ms
  static unsigned long lastNeckMs = 0;
  if (!manualNeck && now - lastNeckMs >= 20) {
    lastNeckMs = now;
    float step = (neckGoalDeg - neckDeg) * NECK_SMOOTH;
    neckDeg += constrain(step, -NECK_MAX_STEP, NECK_MAX_STEP);
    writeNeck(neckDeg);
  }
  delay(1);
}
