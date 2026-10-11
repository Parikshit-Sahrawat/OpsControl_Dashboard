import { useEffect, useRef } from "react";

// Appearance-layer behavior only: keep keyboard interaction inside modal UI.
export default function useDialogFocus(ref, open, onClose) {
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement;
    const controls = () => [...(ref.current?.querySelectorAll('button:not(:disabled),a[href],input:not(:disabled),textarea:not(:disabled),select:not(:disabled),[tabindex="0"]') || [])].filter(node => node.getClientRects().length);
    controls()[0]?.focus();
    const keyboard = event => {
      if (event.key === "Escape") { event.preventDefault(); close.current?.(); }
      if (event.key === "Tab") {
        const elements = controls(), first = elements[0], last = elements.at(-1);
        if (!first) { event.preventDefault(); return; }
        if (event.shiftKey && (document.activeElement === first || !ref.current?.contains(document.activeElement))) {
          event.preventDefault(); last.focus();
        } else if (!event.shiftKey && (document.activeElement === last || !ref.current?.contains(document.activeElement))) {
          event.preventDefault(); first.focus();
        }
      }
    };
    document.addEventListener("keydown", keyboard);
    return () => {
      document.removeEventListener("keydown", keyboard);
      if (previous?.isConnected) previous.focus();
    };
  }, [open, ref]);
}
