import { useEffect, useState } from 'react';

/**
 * Shows a one-time toast when any API call takes longer than `delay` ms.
 * Disappears when `loading` goes false. Never shows again this session.
 *
 * Props:
 *   loading  – true while any tracked API call is in-flight
 *   delay    – ms before toast appears (default 3000)
 */
export default function ColdStartToast({ loading, delay = 3000 }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Only ever show once per browser session
    if (sessionStorage.getItem('cold-start-shown')) return;

    if (!loading) {
      setVisible(false);
      return;
    }

    const timer = setTimeout(() => {
      setVisible(true);
      sessionStorage.setItem('cold-start-shown', '1');
    }, delay);

    return () => clearTimeout(timer);
  }, [loading, delay]);

  // Hide as soon as loading finishes
  useEffect(() => {
    if (!loading) setVisible(false);
  }, [loading]);

  if (!visible) return null;

  return (
    <div
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 pointer-events-none"
      style={{ animation: 'fadeInUp 0.3s ease both' }}
    >
      <div
        className="px-5 py-3 rounded-full text-sm text-white"
        style={{ background: 'rgba(30, 30, 30, 0.82)', backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)', whiteSpace: 'nowrap' }}
      >
        Waking up the server — this can take up to 30 seconds on first load
      </div>
    </div>
  );
}
