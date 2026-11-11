# Host software (Mac mini)

The conversation loop runs on an M4 Mac mini.

| File | Purpose |
|---|---|
| `skull.py` | Main loop: waits for a visitor, then runs Whisper (MLX) speech-to-text, Claude (Haiku) and macOS `say`, and streams jaw sync over UDP |
| `skull_british.py` | Same loop with a normal-paced UK voice |
| `setup.sh` | One-time dependency install |
| `start_skull.command` | Double-click or Login Item launcher |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for your API key and settings |

## Notes

- **Voices:** better macOS voices download from System Settings → Accessibility → Read & Speak.
- **Audio devices:** the input and output devices are picked by name, not by index, which avoids sample-rate mismatches with the USB mic array.
- **Presence:** the ESP32 repeats its presence state every 2 s, so the host can't get stuck waiting for a visitor.
- **Conversation length:** there is no fixed turn limit. The conversation ends when the visitor leaves or goes quiet.

**Never commit `.env`.** It's already in `.gitignore`.
