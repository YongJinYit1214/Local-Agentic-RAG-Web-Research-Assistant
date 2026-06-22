"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { FileText, Globe2, MessageSquare, Plus, Send, Trash2, Upload } from "lucide-react";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
};

type Source = {
  title: string;
  url?: string | null;
  document?: string | null;
  page?: number | null;
  snippet?: string | null;
};

type Session = {
  session_id: string;
  title: string;
  updated_at: string;
};

type IndexedDocument = {
  document: string;
  chunks: number;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

function newSessionId() {
  return `session_${Date.now()}`;
}

export default function Home() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionId, setSessionId] = useState(newSessionId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [webSearchMode, setWebSearchMode] = useState(false);
  const [status, setStatus] = useState("Ready");
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [documents, setDocuments] = useState<IndexedDocument[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const canSend = input.trim().length > 0 && !isStreaming;

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((response) => {
        setApiOnline(response.ok);
        if (!response.ok) setStatus(`FastAPI is not reachable at ${API_BASE}`);
      })
      .catch(() => {
        setApiOnline(false);
        setStatus(`FastAPI is not reachable at ${API_BASE}`);
      });

    refreshSessions();
    refreshDocuments(sessionId);
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, status]);

  async function loadSession(id: string) {
    setSessionId(id);
    setStatus("Loading chat...");
    const response = await fetch(`${API_BASE}/sessions/${id}/messages`);
    const rows = await response.json();
    setMessages(rows.map((row: ChatMessage) => ({ role: row.role, content: row.content })));
    await refreshDocuments(id);
    setStatus("Ready");
  }

  function startNewChat() {
    setSessionId(newSessionId());
    setMessages([]);
    setDocuments([]);
    setStatus("Ready");
  }

  async function refreshSessions() {
    fetch(`${API_BASE}/sessions`)
      .then((response) => response.json())
      .then(setSessions)
      .catch(() => setSessions([]));
  }

  async function refreshDocuments(id = sessionId) {
    fetch(`${API_BASE}/documents?session_id=${encodeURIComponent(id)}`)
      .then((response) => response.json())
      .then(setDocuments)
      .catch(() => setDocuments([]));
  }

  async function deleteSession(id: string) {
    await fetch(`${API_BASE}/sessions/${encodeURIComponent(id)}`, { method: "DELETE" });
    setSessions((current) => current.filter((session) => session.session_id !== id));
    if (id === sessionId) startNewChat();
  }

  async function deleteDocument(documentName: string) {
    await fetch(`${API_BASE}/documents/${encodeURIComponent(documentName)}?session_id=${encodeURIComponent(sessionId)}`, { method: "DELETE" });
    setDocuments((current) => current.filter((document) => document.document !== documentName));
    setStatus("Document deleted");
  }

  async function clearDocuments() {
    await fetch(`${API_BASE}/documents?session_id=${encodeURIComponent(sessionId)}`, { method: "DELETE" });
    setDocuments([]);
    setStatus("Documents cleared");
  }

  async function uploadDocument(file: File) {
    const formData = new FormData();
    formData.append("session_id", sessionId);
    formData.append("file", file);
    setStatus("Uploading document...");
    const response = await fetch(`${API_BASE}/documents/upload`, {
      method: "POST",
      body: formData
    });
    if (!response.ok) {
      setStatus("Upload failed");
      return;
    }
    const result = await response.json();
    setDocuments((current) => [
      ...current.filter((document) => document.document !== result.filename),
      { document: result.filename, chunks: result.chunks }
    ]);
    setStatus("Document indexed");
  }

  async function sendMessage(event: FormEvent) {
    event.preventDefault();
    if (!canSend) return;

    const userText = input.trim();
    setInput("");
    setIsStreaming(true);
    setStatus("Routing request...");
    setMessages((current) => [
      ...current,
      { role: "user", content: userText },
      { role: "assistant", content: "" }
    ]);

    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: userText,
          web_search_mode: webSearchMode
        })
      });

      if (!response.body) throw new Error("No response stream");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";

        for (const rawEvent of events) {
          const eventLine = rawEvent.split("\n").find((line) => line.startsWith("event:"));
          const dataLine = rawEvent.split("\n").find((line) => line.startsWith("data:"));
          if (!eventLine || !dataLine) continue;
          const eventName = eventLine.replace("event:", "").trim();
          const data = JSON.parse(dataLine.replace("data:", "").trim());

          if (eventName === "status") setStatus(data.message);
          if (eventName === "route") {
            setStatus(`Route: ${data.route} (${Math.round(data.confidence * 100)}%) - ${data.rationale}`);
          }
          if (eventName === "token") {
            setMessages((current) => {
              const next = [...current];
              const last = next[next.length - 1];
              next[next.length - 1] = { ...last, content: last.content + data.token };
              return next;
            });
          }
          if (eventName === "sources") {
            setMessages((current) => {
              const next = [...current];
              const last = next[next.length - 1];
              next[next.length - 1] = { ...last, sources: data.sources };
              return next;
            });
          }
          if (eventName === "error") {
            setStatus(data.message);
            setMessages((current) => {
              const next = [...current];
              const last = next[next.length - 1];
              if (last?.role === "assistant" && !last.content) {
                next[next.length - 1] = { ...last, content: data.message };
              }
              return next;
            });
          }
          if (eventName === "done") setStatus("Ready");
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Request failed";
      setStatus(`${message}. Check that FastAPI is running at ${API_BASE}`);
    } finally {
      setIsStreaming(false);
    }
  }

  const orderedSessions = useMemo(() => sessions.slice(0, 20), [sessions]);

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <MessageSquare size={22} />
          <div>
            <h1>LocalMind</h1>
            <p>Agentic RAG Assistant</p>
          </div>
        </div>
        <button className="new-chat" onClick={startNewChat}>
          <Plus size={17} />
          New chat
        </button>
        <div className="session-list">
          {orderedSessions.map((session) => (
            <div
              key={session.session_id}
              className={session.session_id === sessionId ? "session active" : "session"}
            >
              <button className="session-main" onClick={() => loadSession(session.session_id)}>
                <MessageSquare size={15} />
                <span>{session.title}</span>
              </button>
              <button
                className="session-delete"
                onClick={() => deleteSession(session.session_id)}
                title="Delete chat"
                type="button"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      </aside>

      <section className="chat-panel">
        <header className="topbar">
          <div>
            <h2>Streaming Chat</h2>
            <p>
              {apiOnline === false ? "API offline - " : ""}
              {status}
            </p>
          </div>
          <label className="toggle">
            <input
              type="checkbox"
              checked={webSearchMode}
              onChange={(event) => setWebSearchMode(event.target.checked)}
            />
            <Globe2 size={17} />
            Web Search
          </label>
        </header>

        <div className="messages">
          {messages.length === 0 && (
            <div className="empty-state">
              <h3>Ask from documents, chat history, or the current web.</h3>
              <p>Upload a PDF, ask a question, and switch Web Search on when you want online results.</p>
            </div>
          )}

          {messages.map((message, index) => (
            <article key={index} className={`message ${message.role}`}>
              <div className="bubble">{message.content || (message.role === "assistant" ? "..." : "")}</div>
              {message.sources && message.sources.length > 0 && (
                <div className="sources">
                  {message.sources.map((source, sourceIndex) => (
                    <a
                      key={`${source.title}-${sourceIndex}`}
                      href={source.url ?? undefined}
                      target="_blank"
                      rel="noreferrer"
                      className="source"
                    >
                      <FileText size={14} />
                      <span>
                        [{sourceIndex + 1}] {source.title}
                      </span>
                    </a>
                  ))}
                </div>
              )}
            </article>
          ))}
          <div ref={bottomRef} />
        </div>

        <div className="document-strip">
          {documents.map((document) => (
            <span key={document.document}>
              {document.document} ({document.chunks} chunks)
              <button type="button" onClick={() => deleteDocument(document.document)} title="Delete document">
                <Trash2 size={13} />
              </button>
            </span>
          ))}
          {documents.length > 0 && (
            <button type="button" className="clear-docs" onClick={clearDocuments}>
              Clear docs
            </button>
          )}
        </div>

        <form className="composer" onSubmit={sendMessage}>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.md"
            hidden
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) uploadDocument(file);
              event.currentTarget.value = "";
            }}
          />
          <button type="button" className="icon-button" onClick={() => fileInputRef.current?.click()} title="Upload document">
            <Upload size={19} />
          </button>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask LocalMind..."
            rows={1}
          />
          <button type="submit" className="send-button" disabled={!canSend} title="Send message">
            <Send size={18} />
          </button>
        </form>
      </section>
    </main>
  );
}
