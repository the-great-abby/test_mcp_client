import { useEffect, useRef, useState, useCallback } from 'react';

export type WebSocketStatus = 'connecting' | 'open' | 'closed' | 'error' | 'reconnecting';

interface UseWebSocketOptions {
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  protocols?: string | string[];
}

export function useWebSocket<T = any>(
  url: string,
  { reconnectInterval = 2000, maxReconnectAttempts = 10, protocols }: UseWebSocketOptions = {}
) {
  const [status, setStatus] = useState<WebSocketStatus>('connecting');
  const [messages, setMessages] = useState<T[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const shouldReconnect = useRef(true);

  const connect = useCallback(() => {
    setStatus('connecting');
    const ws = new WebSocket(url, protocols);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('open');
      reconnectAttempts.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setMessages((prev) => [...prev, data]);
      } catch {
        setMessages((prev) => [...prev, event.data]);
      }
    };

    ws.onerror = () => {
      setStatus('error');
    };

    ws.onclose = () => {
      setStatus('closed');
      if (shouldReconnect.current && reconnectAttempts.current < maxReconnectAttempts) {
        setStatus('reconnecting');
        reconnectAttempts.current += 1;
        setTimeout(connect, reconnectInterval);
      }
    };
  }, [url, protocols, reconnectInterval, maxReconnectAttempts]);

  useEffect(() => {
    shouldReconnect.current = true;
    connect();
    return () => {
      shouldReconnect.current = false;
      wsRef.current?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connect]);

  const sendMessage = useCallback((msg: T) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
  }, []);

  return {
    status,
    messages,
    sendMessage,
    latestMessage: messages[messages.length - 1],
    isOpen: status === 'open',
  };
} 