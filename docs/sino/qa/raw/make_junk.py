# Two junk-filter probes: 4.5 s of digital silence, and 4.5 s of faint random room hum (about -50 dBFS).
import array, random, wave
def write(name, samples):
    with wave.open(name, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(array.array("h", samples).tobytes())
n = int(16000 * 4.5)
write("silence.wav", [0] * n)
random.seed(1)
write("room-hum.wav", [random.randint(-100, 100) for _ in range(n)])
