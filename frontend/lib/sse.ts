import { StreamEvent } from "./api";

export interface SSEListener {
  onEvent: (event: StreamEvent) => void;
  onError?: (err: Event) => void;
  onOpen?: () => void;
  onClose?: () => void;
}

export function createSSEConnection(taskId: string, listener: SSEListener): () => void {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const url = `${baseUrl}/tasks/${taskId}/stream`;
  const source = new EventSource(url);

  source.addEventListener("open", () => listener.onOpen?.());
  source.addEventListener("error", (e) => listener.onError?.(e));

  source.addEventListener("message", (e) => {
    try {
      const parsed = JSON.parse(e.data);
      listener.onEvent(parsed as StreamEvent);
    } catch {
      /* ignore invalid lines */
    }
  });

  return () => source.close();
}
