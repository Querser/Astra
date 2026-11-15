import { useEffect, useRef, useState } from "react";
import { api, ApiError, type ChatMessage, type ChatResponse, type Analysis } from "./api";

type Submission = { request_id: string; message: string; at: string };
type Chat = { rows: ChatMessage[]; draft: string; busy: boolean; error: string; retry?: Submission };
type ProfileUpdate = (owner: string, analysis: Analysis) => void;

function readSubmission(owner: string): Submission | null {
  try {
    const data = JSON.parse(sessionStorage.getItem("astra.chat.pending." + owner) || "null");
    if (typeof data?.request_id === "string" && typeof data.message === "string" && typeof data.at === "string") return data;
  } catch { /* Invalid session checkpoint. Durable history remains on the API. */ }
  return null;
}

function initial(owner: string): Chat {
  return { rows: [], busy: false, error: "", draft: sessionStorage.getItem("astra.chat.draft." + owner) || "" };
}

function mergeRows(owner: string, previous: ChatMessage[], incoming: ChatMessage[]) {
  const rows = new Map<string, ChatMessage>();
  for (const item of [...previous, ...incoming]) {
    if (item.crew_member_id !== owner) continue;
    const key = item.request_id ? item.request_id + "/" + item.role : item.id;
    if (item.id.startsWith("pending-") && rows.has(key)) continue;
    rows.set(key, item);
  }
  return Array.from(rows.values()).sort((a, b) => a.created_at.localeCompare(b.created_at) || a.id.localeCompare(b.id));
}

export function useProfileChat(owner: string, onAnalysis: ProfileUpdate) {
  const [chats, setChats] = useState<Record<string, Chat>>({});
  const active = useRef(new Map<string, string>());
  const state = chats[owner] ?? initial(owner);
  const update = (id: string, action: (chat: Chat) => Chat) => {
    setChats(old => ({ ...old, [id]: action(old[id] ?? initial(id)) }));
  };
  const merge = (id: string, rows: ChatMessage[]) => {
    update(id, chat => ({ ...chat, rows: mergeRows(id, chat.rows, rows) }));
  };
  const draft = (text: string) => {
    sessionStorage.setItem("astra.chat.draft." + owner, text);
    update(owner, chat => ({ ...chat, draft: text }));
  };

  function release(id: string, submission: Submission, message: string) {
    sessionStorage.removeItem("astra.chat.pending." + id);
    update(id, chat => ({ ...chat, retry: undefined, error: message,
      rows: chat.rows.filter(row => row.id !== "pending-" + submission.request_id) }));
    // The request may have committed the user turn before the connection ended.
    void api<ChatMessage[]>("/assistant/chat/" + id)
      .then(rows => merge(id, rows))
      .catch(() => {});
  }

  async function dispatch(id: string, submission: Submission) {
    if (active.current.has(id)) return;
    const key = submission.request_id;
    active.current.set(id, key);
    sessionStorage.setItem("astra.chat.pending." + id, JSON.stringify(submission));
    const pending: ChatMessage = { id: "pending-" + key, request_id: key, crew_member_id: id,
      role: "user", body: submission.message, created_at: submission.at, source_report_id: null,
      analysis_result_id: null, citations: [], legacy: false };
    update(id, chat => ({ ...chat, rows: mergeRows(id, chat.rows, [pending]), busy: true, error: "", retry: undefined }));
    try {
      const reply = await api<ChatResponse>("/assistant/chat", { method: "POST",
        body: JSON.stringify({ crew_member_id: id, request_id: key, message: submission.message }) });
      if (reply.crew_member_id !== id || reply.request_id !== key ||
          reply.messages.some(row => row.crew_member_id !== id || row.request_id !== key)) {
        throw new Error("Failed to match response with profile request.");
      }
      sessionStorage.removeItem("astra.chat.pending." + id);
      merge(id, reply.messages);
      onAnalysis(id, reply.analysis);
    } catch (error) {
      if (error instanceof ApiError && [400, 403, 404, 409, 422].includes(error.status)) {
        release(id, submission, error.message);
      } else {
        update(id, chat => ({ ...chat, error: String(error), retry: submission }));
      }
    } finally {
      active.current.delete(id);
      update(id, chat => ({ ...chat, busy: false }));
    }
  }

  useEffect(() => {
    if (!owner) return;
    let current = true;
    void api<ChatMessage[]>("/assistant/chat/" + owner)
      .then(rows => { if (current) merge(owner, rows); })
      .catch(error => { if (current) update(owner, chat => ({ ...chat, error: String(error) })); });
    const checkpoint = readSubmission(owner);
    if (checkpoint) void dispatch(owner, checkpoint);
    return () => { current = false; };
  }, [owner]);

  function send(message: string) {
    message = message.trim();
    if (!owner || !message || active.current.has(owner) || readSubmission(owner)) return;
    draft("");
    return dispatch(owner, { request_id: crypto.randomUUID(), message, at: new Date().toISOString() });
  }

  return { state, merge, draft, send,
    retry: () => state.retry && dispatch(owner, state.retry),
    dismiss: () => state.retry && release(owner, state.retry, ""),
  };
}
