import type { AudioFormatMsg } from "./wsProtocol";

export class PcmStreamPlayer {
  private ctx: AudioContext | null = null;
  private node: AudioWorkletNode | null = null;
  private currentFormat: AudioFormatMsg | null = null;

  async init(format: AudioFormatMsg) {
    const sameFormat =
      this.currentFormat &&
      this.currentFormat.sample_rate === format.sample_rate &&
      this.currentFormat.channels === format.channels &&
      this.currentFormat.sample_width === format.sample_width &&
      this.currentFormat.encoding === format.encoding;

    if (sameFormat && this.ctx && this.node) {
      if (this.ctx.state !== "running") {
        await this.ctx.resume();
      }
      return;
    }

    await this.close();

    this.currentFormat = format;
    this.ctx = new AudioContext({
      sampleRate: format.sample_rate,
    });

    await this.ctx.audioWorklet.addModule("/audio-stream-processor.js");

    this.node = new AudioWorkletNode(this.ctx, "pcm-stream-processor", {
      numberOfInputs: 0,
      numberOfOutputs: 1,
      outputChannelCount: [Math.min(Math.max(format.channels, 1), 2)],
    });

    this.node.connect(this.ctx.destination);

    if (this.ctx.state !== "running") {
      await this.ctx.resume();
    }
  }

  async prime() {
    await this.init({
      type: "audio_format",
      encoding: "pcm_s16le",
      sample_rate: 22050,
      channels: 1,
      sample_width: 2,
    });
  }

  enqueuePcm16(arrayBuffer: ArrayBuffer) {
    if (!this.node) return;

    const view = new DataView(arrayBuffer);
    const sampleCount = arrayBuffer.byteLength / 2;
    const float32 = new Float32Array(sampleCount);

    for (let i = 0; i < sampleCount; i++) {
      const sample = view.getInt16(i * 2, true);
      float32[i] = sample / 32768;
    }

    this.node.port.postMessage(float32, [float32.buffer]);
  }

  reset() {
    this.node?.port.postMessage({ type: "reset" });
  }

  async hardReset() {
    this.reset();
    if (this.ctx && this.ctx.state !== "running") {
      await this.ctx.resume();
    }
  }

  async close() {
    if (this.node) {
      this.node.disconnect();
      this.node = null;
    }

    if (this.ctx) {
      await this.ctx.close();
      this.ctx = null;
    }

    this.currentFormat = null;
  }
}
