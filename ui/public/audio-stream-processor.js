class PCMStreamProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.queue = [];
    this.currentChunk = null;
    this.currentIndex = 0;

    this.port.onmessage = (event) => {
      const data = event.data;

      if (data?.type === "reset") {
        this.queue = [];
        this.currentChunk = null;
        this.currentIndex = 0;
        return;
      }

      if (data instanceof Float32Array) {
        this.queue.push(data);
      }
    };
  }

  process(inputs, outputs) {
    const output = outputs[0];
    const left = output[0];
    const right = output[1];

    for (let i = 0; i < left.length; i++) {
      if (!this.currentChunk || this.currentIndex >= this.currentChunk.length) {
        this.currentChunk = this.queue.length > 0 ? this.queue.shift() : null;
        this.currentIndex = 0;
      }

      const sample = this.currentChunk ? this.currentChunk[this.currentIndex++] : 0;

      left[i] = sample;
      if (right) {
        right[i] = sample;
      }
    }

    return true;
  }
}

registerProcessor("pcm-stream-processor", PCMStreamProcessor);