import { useLayoutEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { ScrollPanel } from './ScrollPanel';
import './WorkspaceDialog.css';

export function WorkspaceDialog({
  open,
  title,
  onClose,
  children,
  resetKey = '',
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  resetKey?: string;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const close = useRef(onClose);
  useLayoutEffect(() => {
    close.current = onClose;
  }, [onClose]);
  useLayoutEffect(() => {
    if (!open || !dialog.current) return;
    const node = dialog.current;
    const origin =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    node.showModal();
    const background = [...document.body.children].filter(
      (element): element is HTMLElement =>
        element instanceof HTMLElement && !element.contains(node),
    );
    const inert = background.map((element) => element.inert);
    background.forEach((element) => {
      element.inert = true;
    });
    node.querySelector<HTMLElement>('[data-dialog-autofocus]')?.focus();
    return () => {
      node.close();
      background.forEach((element, index) => {
        element.inert = inert[index]!;
      });
      if (origin?.isConnected) {
        origin.focus();
        // 原生对话框关闭时可能再次恢复内部焦点；在关闭提交后恢复入口。
        queueMicrotask(() => {
          if (
            origin.isConnected &&
            !document.querySelector('dialog[open]:not([data-inline="true"])')
          )
            origin.focus();
        });
      }
    };
  }, [open]);
  return (
    <dialog
      ref={dialog}
      className="workspace-dialog"
      aria-label={title}
      onCancel={(event) => {
        event.preventDefault();
        close.current();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) close.current();
      }}
      onKeyDown={(event) => {
        if (event.key !== 'Tab') return;
        const items = [
          ...event.currentTarget.querySelectorAll<HTMLElement>(
            'button:not(:disabled),input:not(:disabled),a[href],select:not(:disabled),textarea:not(:disabled),summary',
          ),
        ].filter(
          (element) =>
            element.getClientRects().length && !element.closest('[hidden]'),
        );
        const first = items[0],
          last = items.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        }
        if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }}
    >
      <div className="workspace-dialog-body">
        <header>
          <h2>{title}</h2>
          <button type="button" onClick={onClose} aria-label={`关闭${title}`}>
            关闭
          </button>
        </header>
        <ScrollPanel active={open} label={title} resetKey={resetKey}>
          {children}
        </ScrollPanel>
      </div>
    </dialog>
  );
}
