// eye_art.h: original eye renderer for the talking skull's GC9A01 displays.
//
// Draws one 240x240 eye frame into a 16-bit LovyanGFX sprite buffer:
//   eyeart::render(buf, gx, gy, pupil, lid, squint)
//     gx, gy  gaze, -1..1 (right / down positive)
//     pupil   pupil radius in pixels
//     lid     blink, 0 = open .. 1 = closed
//     squint  extra upper-lid droop, 0..1
//
// The artwork (sclera, polar iris map, glints) is in eye_art_data.h, generated
// procedurally by tools/eyegen/eyegen.py. To change the eye color, re-run the generator.
#pragma once
#include <stdint.h>
#include <math.h>
#include <stdlib.h>
#include "eye_art_data.h"

namespace eyeart {

constexpr int W = 240, H = 240;
constexpr int IRIS_R = 62;          // iris radius on screen, pixels
constexpr int GAZE_PX = 52;         // how far the iris travels at full gaze
constexpr int LUT_R = IRIS_R + 2;
constexpr int LUT_N = 2 * LUT_R + 1;
constexpr uint16_t LID = 0x0000;    // eyelid / socket color
// The pupil color comes from pupil_ramp in eye_art_data.h (center -> edge): near-black for
// normal eyes, or a hot glow for --pupil glow. Indexing by the fraction of the pupil radius
// keeps the glow the same shape as the pupil dilates.

// Polar lookup for one quadrant-free disk: distance (half pixels) and angle (0..255).
// Built once on first use, into PSRAM if available.
static uint8_t *lutD = nullptr, *lutA = nullptr;

static void buildLut() {
  size_t n = (size_t)LUT_N * LUT_N;
#ifdef ESP32
  lutD = (uint8_t *)ps_malloc(n);
  lutA = (uint8_t *)ps_malloc(n);
#else
  lutD = (uint8_t *)malloc(n);
  lutA = (uint8_t *)malloc(n);
#endif
  for (int y = 0; y < LUT_N; y++) {
    for (int x = 0; x < LUT_N; x++) {
      float dx = x - LUT_R, dy = y - LUT_R;
      float d = sqrtf(dx * dx + dy * dy) * 2.0f;
      float a = atan2f(dy, dx);
      if (a < 0) a += 2.0f * (float)M_PI;
      lutD[y * LUT_N + x] = (uint8_t)(d > 255 ? 255 : d);
      lutA[y * LUT_N + x] = (uint8_t)((int)(a * (IRIS_A / (2.0f * (float)M_PI))) & (IRIS_A - 1));
    }
  }
}

// Scale a byte-swapped RGB565 pixel by k/256
static inline uint16_t shade(uint16_t p, int k) {
  uint16_t c = (uint16_t)((p >> 8) | (p << 8));
  int r = ((c >> 11) & 31) * k >> 8, g = ((c >> 5) & 63) * k >> 8, b = (c & 31) * k >> 8;
  c = (uint16_t)((r << 11) | (g << 5) | b);
  return (uint16_t)((c >> 8) | (c << 8));
}

// Blend a byte-swapped RGB565 pixel toward white by a/255
static inline uint16_t toWhite(uint16_t p, int a) {
  uint16_t c = (uint16_t)((p >> 8) | (p << 8));
  int r = (c >> 11) & 31, g = (c >> 5) & 63, b = c & 31;
  r += ((31 - r) * a) >> 8; g += ((63 - g) * a) >> 8; b += ((31 - b) * a) >> 8;
  c = (uint16_t)((r << 11) | (g << 5) | b);
  return (uint16_t)((c >> 8) | (c << 8));
}

inline void render(uint16_t *buf, float gx, float gy, float pupil, float lid, float squint) {
  if (!lutD) buildLut();
  if (!lutD || !lutA) return;

  gx = gx < -1 ? -1 : gx > 1 ? 1 : gx;
  gy = gy < -1 ? -1 : gy > 1 ? 1 : gy;
  lid = lid < 0 ? 0 : lid > 1 ? 1 : lid;
  if (pupil < 8) pupil = 8;
  if (pupil > IRIS_R - 12) pupil = IRIS_R - 12;

  const int cx = W / 2 + (int)lroundf(gx * GAZE_PX);
  const int cy = H / 2 + (int)lroundf(gy * GAZE_PX);

  // Foreshortening: the iris narrows as it turns away from center, like a disk on a ball.
  // inv = 256 / scale in 8.8 fixed point.
  const float sx = 1.0f - 0.16f * fabsf(gx), sy = 1.0f - 0.16f * fabsf(gy);
  const int invX = (int)(256.0f / sx), invY = (int)(256.0f / sy);
  const int rx = (int)(IRIS_R * sx) + 1, ry = (int)(IRIS_R * sy) + 1;

  const int P2 = (int)(pupil * 2.0f), R2 = IRIS_R * 2;
  const int span = R2 - P2;

  // Eyelids: curved edges, following vertical gaze, closing on a blink
  const float down = gy > 0 ? gy : 0, up = gy < 0 ? -gy : 0;
  const float upper = 12 + down * 35 + squint * 45 + lid * 125;
  const float lower = 8 + up * 25 + lid * 120;
  int16_t top[W], bot[W];
  for (int x = 0; x < W; x++) {
    float t = (x - W / 2) / (float)(W / 2);
    top[x] = (int16_t)(upper + 46 * t * t);
    bot[x] = (int16_t)(H - lower - 34 * t * t);
  }

  constexpr int SHADOW = 14;  // soft shadow under the upper lid
  for (int y = 0; y < H; y++) {
    uint16_t *row = buf + y * W;
    const uint16_t *srow = sclera + y * SCLERA_W;
    const int dy = y - cy;
    const bool irisRow = dy >= -ry && dy <= ry;
    const int ly = irisRow ? ((dy * invY) >> 8) + LUT_R : 0;
    const bool lutRow = irisRow && ly >= 0 && ly < LUT_N;
    for (int x = 0; x < W; x++) {
      if (y < top[x] || y >= bot[x]) { row[x] = LID; continue; }
      uint16_t p = srow[x];
      const int dx = x - cx;
      if (lutRow && dx >= -rx && dx <= rx) {
        const int lx = ((dx * invX) >> 8) + LUT_R;
        if (lx >= 0 && lx < LUT_N) {
          const int i = ly * LUT_N + lx;
          const int d = lutD[i];
          if (d < P2) {
            p = pupil_ramp[d * PUPIL_N / P2];
          } else if (d < R2) {
            int r = (d - P2) * (IRIS_RAD - 1) / span;
            p = iris[r * IRIS_A + lutA[i]];
          } else if (d < R2 + 2) {
            p = shade(p, 150);   // soften the iris edge into the sclera
          }
        }
      }
      const int s = y - top[x];
      if (s < SHADOW) p = shade(p, 120 + s * (136 / SHADOW));
      row[x] = p;
    }
  }

  // Corneal reflections travel with the iris
  for (int j = 0; j < GLINT_H; j++) {
    const int y = cy + GLINT_Y0 + j;
    if (y < 0 || y >= H) continue;
    for (int i = 0; i < GLINT_W; i++) {
      const int x = cx + GLINT_X0 + i;
      if (x < 0 || x >= W || y < top[x] + 4 || y >= bot[x]) continue;
      const int a = glint[j * GLINT_W + i];
      if (a > 4) buf[y * W + x] = toWhite(buf[y * W + x], a);
    }
  }
}

}  // namespace eyeart
