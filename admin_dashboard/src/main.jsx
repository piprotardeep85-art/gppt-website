import React from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const metrics = [
  ['Total users', '1,248', '+12%'],
  ['Job scans', '3,842', '+18%'],
  ['High-risk detections', '186', '+8%'],
  ['Pending reports', '24', 'Review'],
];

function App() {
  return (
    <div className="app">
      <aside>
        <div className="brand"><span>AJ</span><strong>AI JobTrust</strong></div>
        <nav>
          <a className="active" href="#dashboard">Dashboard</a>
          <a href="#reports">Reports</a>
          <a href="#companies">Companies</a>
          <a href="#analytics">Analytics</a>
          <a href="#audit">Audit logs</a>
        </nav>
      </aside>
      <main>
        <header>
          <div><p>ADMIN WORKSPACE</p><h1>Moderation Overview</h1></div>
          <button>Admin profile</button>
        </header>
        <section className="metrics">
          {metrics.map(([label, value, change]) => (
            <article key={label}>
              <p>{label}</p><div><strong>{value}</strong><span>{change}</span></div>
            </article>
          ))}
        </section>
        <section className="grid">
          <article className="panel">
            <div className="panel-head"><h2>Detection activity</h2><span>Last 7 days</span></div>
            <div className="chart">
              {[42, 58, 36, 72, 64, 84, 78].map((height, index) => <i key={index} style={{ height: `${height}%` }} />)}
            </div>
          </article>
          <article className="panel">
            <div className="panel-head"><h2>Recent reports</h2><span>24 pending</span></div>
            <div className="reports">
              <div><b>Advance fee request</b><small>Payment fraud · 8 min ago</small></div>
              <div><b>Unknown recruiter domain</b><small>Impersonation · 23 min ago</small></div>
              <div><b>OTP credential request</b><small>Personal data theft · 1 hr ago</small></div>
            </div>
          </article>
        </section>
        <div className="notice">Development dashboard · Connect protected backend APIs and Supabase roles before production use.</div>
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
