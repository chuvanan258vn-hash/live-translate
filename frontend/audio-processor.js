// Chay trong AudioWorklet: nhan Float32 (da o 16kHz vi AudioContext set sampleRate=16000),
// chuyen sang Int16 PCM va gui ve main thread theo tung goi ~100ms.
class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = [];
    this._targetSamples = 1600; // 0.1s @ 16kHz
  }

  process(inputs) {
    const input = inputs[0];
    if (input && input[0]) {
      const channel = input[0];
      for (let i = 0; i < channel.length; i++) {
        let s = Math.max(-1, Math.min(1, channel[i]));
        this._buffer.push(s < 0 ? s * 0x8000 : s * 0x7fff);
      }
      if (this._buffer.length >= this._targetSamples) {
        const pcm = new Int16Array(this._buffer);
        this.port.postMessage(pcm.buffer, [pcm.buffer]);
        this._buffer = [];
      }
    }
    return true; // giu node song
  }
}

registerProcessor('pcm-processor', PCMProcessor);
