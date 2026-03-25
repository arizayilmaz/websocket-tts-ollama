import { useRef } from "react";
import { PcmStreamPlayer } from "../lib/PcmStreamPlayer";
import type { AudioFormatMsg } from "../lib/wsProtocol";

export type AudioPlayerController = {
  prime: () => Promise<void>;
  init: (format: AudioFormatMsg) => Promise<void>;
  enqueue: (buffer: ArrayBuffer) => void;
  reset: () => Promise<void>;
  close: () => Promise<void>;
};

type Options = {
  createPlayer?: () => PcmStreamPlayer;
};

export function useAudioPlayer(options: Options = {}): AudioPlayerController {
  const playerRef = useRef<PcmStreamPlayer | null>(null);

  const getPlayer = () => {
    if (!playerRef.current) {
      playerRef.current = options.createPlayer?.() ?? new PcmStreamPlayer();
    }
    return playerRef.current;
  };

  return {
    prime: async () => {
      await getPlayer().prime();
    },
    init: async (format) => {
      await getPlayer().init(format);
    },
    enqueue: (buffer) => {
      getPlayer().enqueuePcm16(buffer);
    },
    reset: async () => {
      if (!playerRef.current) {
        return;
      }
      await playerRef.current.hardReset();
    },
    close: async () => {
      if (!playerRef.current) {
        return;
      }
      await playerRef.current.close();
      playerRef.current = null;
    },
  };
}
