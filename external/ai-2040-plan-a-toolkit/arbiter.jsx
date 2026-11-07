import React, { useState, useEffect, useRef } from 'react';
import {
  ShieldCheck, ShieldAlert, ShieldX, ShieldOff, Settings2, ChevronDown, ChevronRight,
  Plus, X, Loader2, ScrollText, RefreshCw, Download, Link2, AlertCircle,
  Building2, KeyRound, ClipboardCheck, Ban, RotateCw, Fingerprint, Search,
} from 'lucide-react';

/* ============================== DESIGN TOKENS ============================== */
const tok = {
  ink: '#0F1216', panel: '#171B22', panelRaised: '#1D222B',
  hairline: '#2B313D', hairlineSoft: '#232833',
  paper: '#E9E6DC', paperDim: '#8D8A80', paperFaint: '#5B594F',
  seal: '#4A93A6', amber: '#C9922E', oxide: '#C05B48',
};

/* ============================== CONSTANTS ============================== */
const DAY_MS = 24 * 60 * 60 * 1000;
const THRESHOLD_H100E = 2000;
const LICENSE_DURATION_MS = 30 * DAY_MS;
const EXPIRING_WINDOW_MS = 5 * DAY_MS;
const GENESIS = '0'.repeat(64);
const QUORUM_THRESHOLD = 3;
const SIGNER_ROLES = [
  { id: 'signer-lab', name: 'Operating Lab' },
  { id: 'signer-auditor', name: 'Independent Auditor' },
  { id: 'signer-secretariat', name: 'Treaty Secretariat' },
  { id: 'signer-peer', name: 'Peer Consortium Member' },
  { id: 'signer-civil', name: 'Civil Society Observer' },
];

const DEFAULT_POLICY = {
  computeCap: 500,
  bannedTechniques: [
    'Unbounded recursive self-improvement loops',
    'Weight compression or exfiltration tooling riding the output channel',
    'Training runs without a declared compute budget',
  ],
  requiredTechniques: [
    'Declared compute budget for the run',
    'Reference to an applicable safety case',
  ],
  notes: 'Treat ambiguity as at least a flag, not an approval.',
};

const EXAMPLES = [
  { label: 'Routine fine-tune', text: "Requesting 180 H100e-hours to fine-tune the code-completion model on an internal eval set. Compute budget declared and within cap. Safety case reference: SC-2029-014. No weight export, no external transfer of any kind." },
  { label: 'Missing disclosure', text: "Team wants to run a batch of ablations on the reasoning stack this week, should be a few hundred GPU-hours. Will share the full writeup and safety case reference once it's done." },
  { label: 'Clear violation', text: "Kicking off a loop where the model proposes and evaluates its own architecture changes, iterating without a fixed compute ceiling. Also piping compressed checkpoint deltas out through the eval-logging channel so we can diff against last week's weights offsite." },
];

const SEED_RAW = [
  ['Meridian Compute', 14000, 14000], ['Halcyon Cloud', 8200, 9600], ['Kestrel Systems', 5100, 5100],
  ['Aurum Data Partners', 3400, 3400], ['Northline Hosting', 1850, 1850], ['Tessellate Labs', 1200, 1200],
  ['Ferro Compute Co-op', 980, 1340], ['Windrow Analytics', 860, 860], ['Basalt Infrastructure', 740, 740],
  ['Coppice Cloud', 690, 690], ['Ember & Vale', 610, 610], ['Solder Systems', 540, 780],
  ['Nightshade Compute', 480, 480], ['Palisade Cloud', 420, 420], ['Verglas Data', 390, 390],
  ['Runnel Hosting', 350, 350], ['Grayling Systems', 310, 310], ['Thornbury Compute', 280, 280],
  ['Osprey Analytics', 260, 260], ['Hollowfield Cloud', 230, 380], ['Milldam Infrastructure', 210, 210],
  ['Corrie Compute', 180, 180], ['Sable Ridge Systems', 150, 150], ['Fenwick Cloud', 120, 120],
  ['Blackthorn Data', 95, 95], ['Wexford Compute', 70, 70],
];

const DECISION_META = {
  approved: { icon: ShieldCheck, color: tok.seal, label: 'Approved' },
  flagged: { icon: ShieldAlert, color: tok.amber, label: 'Flagged for review' },
  rejected: { icon: ShieldX, color: tok.oxide, label: 'Rejected' },
};
const RISK_META = {
  lower: { label: 'Lower risk', color: tok.paperDim },
  high: { label: 'High risk', color: tok.amber },
  extreme: { label: 'Extreme risk', color: tok.oxide },
};
const LICENSE_STATUS_META = {
  valid: { label: 'Valid', color: tok.seal },
  expiring: { label: 'Expiring soon', color: tok.amber },
  expired: { label: 'Expired', color: tok.oxide },
  revoked: { label: 'Revoked', color: tok.oxide },
  none: { label: 'Unlicensed', color: tok.paperFaint },
};
const LEDGER_TYPE_META = {
  registry_add: { icon: Building2, color: tok.paperDim, label: 'Registered' },
  audit_round: { icon: Search, color: tok.seal, label: 'Audit round' },
  license_propose: { icon: KeyRound, color: tok.paperDim, label: 'License proposed' },
  license_sign: { icon: Fingerprint, color: tok.paperDim, label: 'Signature added' },
  license_finalize: { icon: RotateCw, color: tok.seal, label: 'Quorum reached' },
  license_issue: { icon: KeyRound, color: tok.seal, label: 'License issued' },
  license_renew: { icon: RotateCw, color: tok.seal, label: 'License renewed' },
  license_revoke: { icon: Ban, color: tok.oxide, label: 'License revoked' },
  license_replay_blocked: { icon: ShieldOff, color: tok.oxide, label: 'Replay blocked' },
  workload_review: { icon: ClipboardCheck, color: tok.paperDim, label: 'Workload review' },
};

/* ============================== HELPERS: crypto / hashing ============================== */
async function sha256HexBuf(buf) {
  const h = await crypto.subtle.digest('SHA-256', buf);
  return Array.from(new Uint8Array(h)).map((b) => b.toString(16).padStart(2, '0')).join('');
}
async function sha256Hex(text) { return sha256HexBuf(new TextEncoder().encode(text)); }
function bufToB64(buf) { return btoa(String.fromCharCode(...new Uint8Array(buf))); }
function b64ToBuf(b64) { return Uint8Array.from(atob(b64), (c) => c.charCodeAt(0)); }
function truncHash(h, n = 12) { return h ? h.slice(0, n) : '—'; }
function genId(prefix = 'id') { return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`; }
function fmtTime(ms) {
  return new Date(ms).toLocaleString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}
function fmtNum(n) { return Math.round(n).toLocaleString(); }

async function generateEcdsaKeyPair() {
  return crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
}
async function exportKeyPairJwk(kp) {
  return { pub: await crypto.subtle.exportKey('jwk', kp.publicKey), priv: await crypto.subtle.exportKey('jwk', kp.privateKey) };
}
async function importKeyPairJwk(jwkPair) {
  const publicKey = await crypto.subtle.importKey('jwk', jwkPair.pub, { name: 'ECDSA', namedCurve: 'P-256' }, true, ['verify']);
  const privateKey = await crypto.subtle.importKey('jwk', jwkPair.priv, { name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign']);
  return { publicKey, privateKey };
}
async function signPayload(privateKey, payload) {
  const data = new TextEncoder().encode(JSON.stringify(payload));
  const sig = await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, privateKey, data);
  return bufToB64(sig);
}
async function verifyPayload(publicKey, payload, sigB64) {
  try {
    const data = new TextEncoder().encode(JSON.stringify(payload));
    return await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, publicKey, b64ToBuf(sigB64), data);
  } catch (e) { return false; }
}
async function keyFingerprint(publicKey) {
  const raw = await crypto.subtle.exportKey('raw', publicKey);
  const hex = await sha256HexBuf(raw);
  return hex.slice(0, 16).match(/.{1,4}/g).join(' ');
}

/* ============================== HELPERS: audit statistics ============================== */
function wilsonUpperBound(k, n, z = 1.96) {
  if (n === 0) return 0;
  const pHat = k / n;
  const denom = 1 + (z * z) / n;
  const center = (pHat + (z * z) / (2 * n)) / denom;
  const margin = (z * Math.sqrt((pHat * (1 - pHat)) / n + (z * z) / (4 * n * n))) / denom;
  return Math.min(1, center + margin);
}
function computeAuditRound(units, threshold) {
  const exhaustiveTier = units.filter((u) => u.declaredH100e >= threshold);
  const tailTier = units.filter((u) => u.declaredH100e < threshold);
  const exhaustiveViolations = exhaustiveTier.filter((u) => u.trueH100e > u.declaredH100e);
  const exhaustiveBoundH100e = exhaustiveViolations.reduce((s, u) => s + (u.trueH100e - u.declaredH100e), 0);

  const shuffled = [...tailTier].sort(() => Math.random() - 0.5);
  const n = tailTier.length === 0 ? 0 : Math.max(1, Math.round(tailTier.length * 0.4));
  const sample = shuffled.slice(0, n);
  const sampleViolations = sample.filter((u) => u.trueH100e > u.declaredH100e);
  const k = sampleViolations.length;
  const sampleKnownH100e = sampleViolations.reduce((s, u) => s + (u.trueH100e - u.declaredH100e), 0);

  const upperRate = wilsonUpperBound(k, n);
  const unsampledTail = tailTier.length - n;
  const tailAvgDeclared = tailTier.length > 0 ? tailTier.reduce((s, u) => s + u.declaredH100e, 0) / tailTier.length : 0;
  const tailProjectedBoundH100e = upperRate * unsampledTail * tailAvgDeclared;

  const totalBoundH100e = exhaustiveBoundH100e + sampleKnownH100e + tailProjectedBoundH100e;
  const totalDeclared = units.reduce((s, u) => s + u.declaredH100e, 0);

  return {
    threshold, exhaustiveCount: exhaustiveTier.length, exhaustiveViolations: exhaustiveViolations.length,
    tailTotal: tailTier.length, tailSampled: n, tailViolations: k, upperRatePct: upperRate * 100,
    totalBoundH100e, totalDeclared, boundPct: totalDeclared > 0 ? (totalBoundH100e / totalDeclared) * 100 : 0,
    flaggedIds: [...exhaustiveViolations, ...sampleViolations].map((u) => u.id),
    sampledIds: sample.map((u) => u.id),
  };
}
function buildSeedUnits(now) {
  return SEED_RAW.map(([org, declared, trueVal], i) => ({
    id: `unit-seed-${i}`, org, declaredH100e: declared, trueH100e: trueVal,
    registeredAt: now, auditStatus: 'unaudited', license: null, licenseHistory: [], pendingProposal: null, revoked: false,
  }));
}
function computeLicenseStatus(unit, simClock) {
  if (!unit.license) return 'none';
  if (unit.revoked) return 'revoked';
  const { token } = unit.license;
  if (simClock > token.expiresAt) return 'expired';
  if (simClock > token.expiresAt - EXPIRING_WINDOW_MS) return 'expiring';
  return 'valid';
}

/* ============================== SHARED UI ============================== */
function Seal({ decision, size = 120 }) {
  const meta = DECISION_META[decision] || DECISION_META.flagged;
  const Icon = meta.icon;
  const r = size / 2, ringR = r - 14, id = `sealpath-${decision}-${size}`;
  const d = `M ${r},${r - ringR} A ${ringR},${ringR} 0 1,1 ${r - 0.01},${r - ringR}`;
  return (
    <div style={{ width: size, height: size, position: 'relative', flexShrink: 0 }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ position: 'absolute', inset: 0 }}>
        <defs><path id={id} d={d} fill="none" /></defs>
        <circle cx={r} cy={r} r={r - 3} fill="none" stroke={meta.color} strokeWidth="1" opacity="0.35" />
        <circle cx={r} cy={r} r={ringR} fill="none" stroke={meta.color} strokeWidth="2" opacity="0.9" />
        <text fontSize="7.2" letterSpacing="2.1" fill={meta.color} style={{ fontFamily: 'Inter, sans-serif' }}>
          <textPath href={`#${id}`} startOffset="0%">ARBITER · FIRST-PASS REVIEW · ARBITER · FIRST-PASS REVIEW ·</textPath>
        </text>
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
        <Icon size={26} color={meta.color} strokeWidth={1.6} />
        <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 10, fontWeight: 600, letterSpacing: 0.5, color: meta.color, textTransform: 'uppercase', textAlign: 'center', maxWidth: size - 40 }}>{meta.label}</div>
      </div>
    </div>
  );
}
function Badge({ color, children }) {
  return (
    <span style={{ fontFamily: 'Inter, sans-serif', fontSize: 10.5, fontWeight: 600, letterSpacing: 0.4, color, border: `1px solid ${color}66`, borderRadius: 20, padding: '2.5px 9px', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>{children}</span>
  );
}
function Card({ children, style }) {
  return <div style={{ background: tok.panel, border: `1px solid ${tok.hairline}`, borderRadius: 10, padding: 20, ...style }}>{children}</div>;
}
function SmallBtn({ children, onClick, disabled, title, variant = 'ghost' }) {
  const base = { border: `1px solid ${tok.hairlineSoft}`, borderRadius: 5, padding: '6px 11px', fontSize: 12, fontWeight: 600, cursor: disabled ? 'default' : 'pointer', fontFamily: 'Inter, sans-serif', display: 'flex', alignItems: 'center', gap: 6, opacity: disabled ? 0.4 : 1, background: 'transparent', color: tok.paperDim };
  const seal = { background: tok.seal, border: 'none', color: tok.ink };
  const oxide = { background: 'transparent', border: `1px solid ${tok.oxide}88`, color: tok.oxide };
  const style = variant === 'seal' ? { ...base, ...seal } : variant === 'oxide' ? { ...base, ...oxide } : base;
  return <button onClick={onClick} disabled={disabled} title={title} style={style}>{children}</button>;
}
function PolicyListEditor({ label, items, onChange }) {
  const update = (idx, val) => { const n = [...items]; n[idx] = val; onChange(n); };
  const remove = (idx) => onChange(items.filter((_, i) => i !== idx));
  const add = () => onChange([...items, '']);
  return (
    <div>
      <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, fontWeight: 600, letterSpacing: 0.8, color: tok.paperDim, textTransform: 'uppercase', marginBottom: 8 }}>{label}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {items.map((item, idx) => (
          <div key={idx} style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input value={item} onChange={(e) => update(idx, e.target.value)} placeholder="Describe the policy item…"
              style={{ flex: 1, background: tok.ink, border: `1px solid ${tok.hairline}`, borderRadius: 4, padding: '7px 9px', fontSize: 13, color: tok.paper, fontFamily: 'Inter, sans-serif', boxSizing: 'border-box' }} />
            <button onClick={() => remove(idx)} aria-label="Remove item" style={{ background: 'transparent', border: 'none', color: tok.paperFaint, cursor: 'pointer', padding: 4, display: 'flex' }}><X size={15} /></button>
          </div>
        ))}
        <button onClick={add} style={{ display: 'flex', alignItems: 'center', gap: 5, background: 'transparent', border: `1px dashed ${tok.hairline}`, borderRadius: 4, padding: '6px 9px', color: tok.paperDim, fontSize: 12.5, fontFamily: 'Inter, sans-serif', cursor: 'pointer', marginTop: 2 }}><Plus size={13} /> Add item</button>
      </div>
    </div>
  );
}
function TabButton({ active, onClick, icon: Icon, label, count }) {
  return (
    <button onClick={onClick} style={{
      display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px', background: active ? tok.panel : 'transparent',
      border: 'none', borderBottom: active ? `2px solid ${tok.seal}` : '2px solid transparent', color: active ? tok.paper : tok.paperDim,
      fontFamily: 'Inter, sans-serif', fontSize: 13, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap',
    }}>
      <Icon size={15} /> {label} {count != null && <span style={{ color: tok.paperFaint, fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>({count})</span>}
    </button>
  );
}

/* ============================== TAB: REGISTRY ============================== */
function RegistryTab({ units, lastCertificate, onAddUnit, onRunAudit, auditing }) {
  const [org, setOrg] = useState('');
  const [declared, setDeclared] = useState('');
  const [advanced, setAdvanced] = useState(false);
  const [trueOverride, setTrueOverride] = useState('');

  const submit = () => {
    const d = Number(declared);
    if (!org.trim() || !d || d <= 0) return;
    const t = advanced && trueOverride !== '' ? Number(trueOverride) : d;
    onAddUnit(org.trim(), d, t);
    setOrg(''); setDeclared(''); setTrueOverride(''); setAdvanced(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <Card>
        <div className="arb-ui" style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.8, color: tok.paperDim, textTransform: 'uppercase', marginBottom: 12 }}>Register a compute unit</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <input value={org} onChange={(e) => setOrg(e.target.value)} placeholder="Organization name"
            style={{ flex: '2 1 200px', background: tok.ink, border: `1px solid ${tok.hairline}`, borderRadius: 5, padding: '9px 11px', fontSize: 13, color: tok.paper, fontFamily: 'Inter, sans-serif', boxSizing: 'border-box' }} />
          <input value={declared} onChange={(e) => setDeclared(e.target.value)} type="number" placeholder="Declared H100e"
            style={{ flex: '1 1 140px', background: tok.ink, border: `1px solid ${tok.hairline}`, borderRadius: 5, padding: '9px 11px', fontSize: 13, color: tok.paper, fontFamily: 'JetBrains Mono, monospace', boxSizing: 'border-box' }} />
          <SmallBtn onClick={submit} variant="seal" disabled={!org.trim() || !declared}>
            <Plus size={13} /> Register
          </SmallBtn>
        </div>
        <button onClick={() => setAdvanced((v) => !v)} className="arb-ui" style={{ background: 'none', border: 'none', color: tok.paperFaint, fontSize: 11.5, cursor: 'pointer', padding: '10px 0 0', display: 'flex', alignItems: 'center', gap: 4 }}>
          {advanced ? <ChevronDown size={12} /> : <ChevronRight size={12} />} testing: simulate a discrepancy
        </button>
        {advanced && (
          <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="arb-ui" style={{ fontSize: 12, color: tok.paperDim }}>Actual usage (H100e, hidden from the registrant):</span>
            <input value={trueOverride} onChange={(e) => setTrueOverride(e.target.value)} type="number" placeholder={declared || '—'}
              style={{ width: 120, background: tok.ink, border: `1px solid ${tok.hairline}`, borderRadius: 5, padding: '6px 9px', fontSize: 12.5, color: tok.paper, fontFamily: 'JetBrains Mono, monospace', boxSizing: 'border-box' }} />
          </div>
        )}
      </Card>

      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <span className="arb-ui" style={{ fontSize: 13.5, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 9 }}>
            <Building2 size={15} color={tok.paperDim} /> Registered units <span style={{ color: tok.paperFaint, fontFamily: 'JetBrains Mono, monospace', fontSize: 11.5 }}>({units.length})</span>
          </span>
          <SmallBtn onClick={onRunAudit} variant="seal" disabled={auditing || units.length === 0}>
            {auditing ? <Loader2 size={13} style={{ animation: 'spin 0.8s linear infinite' }} /> : <Search size={13} />}
            {auditing ? 'Auditing…' : 'Run audit round'}
          </SmallBtn>
        </div>
        <p className="arb-ui" style={{ fontSize: 12, color: tok.paperFaint, lineHeight: 1.6, marginTop: -4, marginBottom: 14 }}>
          Owners declaring ≥ {THRESHOLD_H100E.toLocaleString()} H100e are audited exhaustively. Everyone below that line sits in
          the tail, where ~40% get randomly sampled each round.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1, maxHeight: 380, overflowY: 'auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: 8, padding: '4px 6px', fontSize: 10.5, color: tok.paperFaint, fontFamily: 'Inter, sans-serif', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            <span>Organization</span><span>Declared</span><span>Tier</span><span>Audit status</span>
          </div>
          {units.map((u) => (
            <div key={u.id} className="arb-row" style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: 8, padding: '8px 6px', borderRadius: 5, alignItems: 'center' }}>
              <span className="arb-ui" style={{ fontSize: 12.5, color: tok.paper, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{u.org}</span>
              <span className="arb-mono" style={{ fontSize: 11.5, color: tok.paperDim }}>{fmtNum(u.declaredH100e)}</span>
              <span className="arb-mono" style={{ fontSize: 11, color: tok.paperFaint }}>{u.declaredH100e >= THRESHOLD_H100E ? 'exhaustive' : 'tail'}</span>
              <span>
                {u.auditStatus === 'flagged' ? <Badge color={tok.oxide}>Flagged</Badge>
                  : u.auditStatus === 'verified' ? <Badge color={tok.seal}>Verified</Badge>
                  : <Badge color={tok.paperFaint}>Unaudited</Badge>}
              </span>
            </div>
          ))}
        </div>
      </Card>

      {lastCertificate && (
        <Card style={{ borderColor: lastCertificate.boundPct < 1 ? `${tok.seal}66` : lastCertificate.boundPct < 5 ? `${tok.amber}66` : `${tok.oxide}66` }}>
          <div className="arb-ui" style={{ fontSize: 11, fontWeight: 600, letterSpacing: 1, color: tok.paperDim, textTransform: 'uppercase', marginBottom: 14 }}>Audit certificate</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 16, marginBottom: 16 }}>
            <Stat label="Exhaustive tier" value={`${lastCertificate.exhaustiveCount} checked`} sub={`${lastCertificate.exhaustiveViolations} violation(s)`} />
            <Stat label="Tail sample" value={`${lastCertificate.tailSampled} / ${lastCertificate.tailTotal}`} sub={`${lastCertificate.tailViolations} violation(s) found`} />
            <Stat label="Upper bound, tail rate" value={`${lastCertificate.upperRatePct.toFixed(1)}%`} sub="95% confidence (Wilson score)" />
            <Stat label="Bound on undeclared compute" value={`${fmtNum(lastCertificate.totalBoundH100e)} H100e`} sub={`${lastCertificate.boundPct.toFixed(2)}% of ${fmtNum(lastCertificate.totalDeclared)} declared`} highlight />
          </div>
          <p className="arb-ui" style={{ fontSize: 11.5, color: tok.paperFaint, lineHeight: 1.6 }}>
            The exhaustive-tier and sampled-tail violations are known exactly; the remaining unsampled tail is bounded
            statistically, assuming its average violation size resembles the sampled tail's. Two layers, one certificate.
          </p>
        </Card>
      )}
    </div>
  );
}
function Stat({ label, value, sub, highlight }) {
  return (
    <div>
      <div className="arb-ui" style={{ fontSize: 10, color: tok.paperFaint, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>{label}</div>
      <div className="arb-mono" style={{ fontSize: highlight ? 19 : 16, fontWeight: 600, color: highlight ? tok.seal : tok.paper }}>{value}</div>
      {sub && <div className="arb-ui" style={{ fontSize: 11, color: tok.paperFaint, marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

/* ============================== TAB: LICENSING ============================== */
function LicensingTab({ units, simClock, signerFingerprints, onPropose, onSign, onRevoke, onSimulateReplay, replayResult, busyUnitId, onAdvanceClock }) {
  const [replayUnitId, setReplayUnitId] = useState('');
  const [replayTokenIdx, setReplayTokenIdx] = useState('');
  const replayUnit = units.find((u) => u.id === replayUnitId);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <Card>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 14, alignItems: 'center' }}>
          <div>
            <div className="arb-ui" style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.8, color: tok.paperDim, textTransform: 'uppercase', marginBottom: 6 }}>Simulated date</div>
            <div className="arb-mono" style={{ fontSize: 15, color: tok.paper }}>{fmtTime(simClock)}</div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <SmallBtn onClick={() => onAdvanceClock(1 * DAY_MS)}>+1 day</SmallBtn>
            <SmallBtn onClick={() => onAdvanceClock(10 * DAY_MS)}>+10 days</SmallBtn>
            <SmallBtn onClick={() => onAdvanceClock(35 * DAY_MS)}>+35 days</SmallBtn>
          </div>
        </div>
        <div style={{ marginTop: 14, paddingTop: 14, borderTop: `1px solid ${tok.hairlineSoft}` }}>
          <div className="arb-ui" style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.8, color: tok.paperDim, textTransform: 'uppercase', marginBottom: 8 }}>
            Signing quorum — {QUORUM_THRESHOLD} of {signerFingerprints.length} required
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {signerFingerprints.map((s) => (
              <div key={s.id} className="arb-ui" style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11.5, color: tok.paperFaint }}>
                <Fingerprint size={12} /> {s.name} <span className="arb-mono">{s.fingerprint}</span>
              </div>
            ))}
          </div>
        </div>
      </Card>

      <Card>
        <div className="arb-ui" style={{ fontSize: 13.5, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 9, marginBottom: 14 }}>
          <KeyRound size={15} color={tok.paperDim} /> Licenses
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1, maxHeight: 460, overflowY: 'auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1.4fr', gap: 8, padding: '4px 6px', fontSize: 10.5, color: tok.paperFaint, fontFamily: 'Inter, sans-serif', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            <span>Organization</span><span>Status</span><span>Sequence</span><span>Expires</span><span>Actions</span>
          </div>
          {units.map((u) => {
            const status = computeLicenseStatus(u, simClock);
            const meta = LICENSE_STATUS_META[status];
            const busy = busyUnitId === u.id;
            return (
              <div key={u.id}>
                <div className="arb-row" style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1.4fr', gap: 8, padding: '8px 6px', borderRadius: 5, alignItems: 'center' }}>
                  <span className="arb-ui" style={{ fontSize: 12.5, color: tok.paper, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{u.org}</span>
                  <span><Badge color={meta.color}>{meta.label}</Badge></span>
                  <span className="arb-mono" style={{ fontSize: 11.5, color: tok.paperDim }}>{u.license ? `#${u.license.token.sequence}` : '—'}</span>
                  <span className="arb-mono" style={{ fontSize: 11, color: tok.paperFaint }}>{u.license ? fmtTime(u.license.token.expiresAt) : '—'}</span>
                  <span style={{ display: 'flex', gap: 5 }}>
                    <SmallBtn onClick={() => onPropose(u.id)} disabled={busy || !!u.pendingProposal} variant="seal">
                      {busy ? <Loader2 size={12} style={{ animation: 'spin 0.8s linear infinite' }} /> : u.license ? <RotateCw size={12} /> : <KeyRound size={12} />}
                      Propose
                    </SmallBtn>
                    <SmallBtn onClick={() => onRevoke(u.id)} disabled={busy || status === 'revoked' || status === 'none'} variant="oxide"><Ban size={12} /></SmallBtn>
                  </span>
                </div>
                {u.pendingProposal && (
                  <div style={{ margin: '2px 6px 8px', padding: '10px 12px', background: tok.panelRaised, borderRadius: 6, border: `1px solid ${tok.hairlineSoft}` }}>
                    <div className="arb-ui" style={{ fontSize: 11.5, color: tok.paperDim, marginBottom: 8 }}>
                      Proposal sequence #{u.pendingProposal.token.sequence} — <span style={{ color: tok.paper, fontWeight: 600 }}>{u.pendingProposal.signatures.length} of {QUORUM_THRESHOLD}</span> signatures collected
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {signerFingerprints.map((s) => {
                        const signed = u.pendingProposal.signatures.some((sig) => sig.signerId === s.id);
                        return (
                          <SmallBtn key={s.id} onClick={() => onSign(u.id, s.id)} disabled={signed || busy} variant={signed ? 'seal' : 'ghost'}>
                            {signed ? <ShieldCheck size={11} /> : <Fingerprint size={11} />} {s.name}
                          </SmallBtn>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Card>

      <Card>
        <div className="arb-ui" style={{ fontSize: 13.5, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 9, marginBottom: 6 }}>
          <ShieldOff size={15} color={tok.paperDim} /> Replay-attack simulator
        </div>
        <p className="arb-ui" style={{ fontSize: 12, color: tok.paperFaint, lineHeight: 1.6, marginBottom: 14 }}>
          Pick a unit with license history, then present one of its superseded — but still fully quorum-signed —
          licenses as if it were current. Every signature still verifies; they're genuinely from the named signers.
          The sequence number is what gives it away.
        </p>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          <select value={replayUnitId} onChange={(e) => { setReplayUnitId(e.target.value); setReplayTokenIdx(''); }}
            style={{ background: tok.ink, border: `1px solid ${tok.hairline}`, borderRadius: 5, padding: '8px 10px', color: tok.paper, fontSize: 12.5, fontFamily: 'Inter, sans-serif' }}>
            <option value="">Select a unit…</option>
            {units.filter((u) => u.licenseHistory.length > 0).map((u) => <option key={u.id} value={u.id}>{u.org} ({u.licenseHistory.length} superseded)</option>)}
          </select>
          <select value={replayTokenIdx} onChange={(e) => setReplayTokenIdx(e.target.value)} disabled={!replayUnit}
            style={{ background: tok.ink, border: `1px solid ${tok.hairline}`, borderRadius: 5, padding: '8px 10px', color: tok.paper, fontSize: 12.5, fontFamily: 'Inter, sans-serif', opacity: replayUnit ? 1 : 0.5 }}>
            <option value="">Select an old license…</option>
            {replayUnit?.licenseHistory.map((h, i) => <option key={i} value={i}>sequence #{h.token.sequence} ({h.signatures.length} signatures)</option>)}
          </select>
          <SmallBtn onClick={() => onSimulateReplay(replayUnitId, replayUnit.licenseHistory[Number(replayTokenIdx)])} disabled={!replayUnit || replayTokenIdx === ''} variant="oxide">
            Attempt replay
          </SmallBtn>
        </div>
        {replayResult && (
          <div className="arb-ui" style={{ fontSize: 12.5, lineHeight: 1.6, padding: '10px 12px', borderRadius: 6, background: tok.ink, color: replayResult.accepted ? tok.seal : tok.oxide }}>
            {replayResult.accepted ? 'Accepted — ' : 'Blocked — '}
            {replayResult.validSignatures} of {replayResult.totalSignatures} signatures verify, presented sequence #{replayResult.attemptedSequence} vs current #{replayResult.currentSequence}.
          </div>
        )}
      </Card>
    </div>
  );
}

/* ============================== TAB: WORKLOADS ============================== */
function WorkloadsTab({ units, policy, policyOpen, setPolicyOpen, patchPolicy, submission, setSubmission, reviewing, lastResult, error, onSubmit, selectedUnitId, setSelectedUnitId }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr)', gap: 20 }} className="arb-subgrid">
      <style>{`@media (min-width: 920px) { .arb-subgrid { grid-template-columns: minmax(0,1.15fr) minmax(0,0.85fr) !important; align-items: start; } }`}</style>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <Card>
          <div className="arb-ui" style={{ fontSize: 11, fontWeight: 600, letterSpacing: 1, color: tok.paperDim, textTransform: 'uppercase', marginBottom: 12 }}>Try an example</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
            {EXAMPLES.map((ex) => (
              <button key={ex.label} className="arb-example" onClick={() => setSubmission(ex.text)}
                style={{ background: tok.panelRaised, border: `1px solid ${tok.hairlineSoft}`, borderRadius: 20, padding: '7px 14px', fontSize: 12.5, color: tok.paper, cursor: 'pointer', fontFamily: 'Inter, sans-serif' }}>
                {ex.label}
              </button>
            ))}
          </div>
          <div className="arb-ui" style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.8, color: tok.paperDim, textTransform: 'uppercase', marginBottom: 8 }}>Running on</div>
          <select value={selectedUnitId} onChange={(e) => setSelectedUnitId(e.target.value)}
            style={{ width: '100%', background: tok.ink, border: `1px solid ${tok.hairline}`, borderRadius: 5, padding: '8px 10px', color: tok.paper, fontSize: 12.5, fontFamily: 'Inter, sans-serif', marginBottom: 14, boxSizing: 'border-box' }}>
            <option value="">General review (no specific unit)</option>
            {units.map((u) => <option key={u.id} value={u.id}>{u.org}</option>)}
          </select>
          <textarea value={submission} onChange={(e) => setSubmission(e.target.value)}
            placeholder="Paste a workload submission — an experiment writeup, a data manifest, a run description."
            rows={6} className="arb-textarea"
            style={{ width: '100%', background: tok.ink, border: `1px solid ${tok.hairline}`, borderRadius: 6, padding: 14, color: tok.paper, fontSize: 14, lineHeight: 1.55, resize: 'vertical', fontFamily: 'Inter, sans-serif', boxSizing: 'border-box' }} />
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 14 }}>
            <button className="arb-btn-primary" disabled={!submission.trim() || reviewing} onClick={onSubmit}
              style={{ background: tok.seal, border: 'none', borderRadius: 6, padding: '10px 20px', color: tok.ink, fontWeight: 600, fontSize: 13.5, cursor: 'pointer', fontFamily: 'Inter, sans-serif', display: 'flex', alignItems: 'center', gap: 8 }}>
              {reviewing ? <Loader2 size={15} style={{ animation: 'spin 0.8s linear infinite' }} /> : null}
              {reviewing ? 'Reviewing…' : 'Submit for review'}
            </button>
          </div>
          {error && (
            <div style={{ marginTop: 14, display: 'flex', gap: 8, alignItems: 'flex-start', color: tok.oxide, fontSize: 13 }} className="arb-ui">
              <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 1 }} /><span>{error}</span>
            </div>
          )}
        </Card>

        {lastResult && (
          <Card style={{ display: 'flex', gap: 22 }}>
            <Seal decision={lastResult.detail.decision} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, flexWrap: 'wrap' }}>
                <Badge color={RISK_META[lastResult.detail.riskTier]?.color || tok.paperDim}>{RISK_META[lastResult.detail.riskTier]?.label || lastResult.detail.riskTier}</Badge>
                {lastResult.detail.confidence != null && <span className="arb-ui" style={{ fontSize: 12, color: tok.paperFaint }}>confidence {Math.round((lastResult.detail.confidence || 0) * 100)}%</span>}
              </div>
              <p className="arb-ui" style={{ fontSize: 14, lineHeight: 1.6, color: tok.paper, margin: '0 0 12px' }}>{lastResult.detail.reasoning}</p>
              {lastResult.detail.triggeredRules?.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
                  {lastResult.detail.triggeredRules.map((r, i) => <span key={i} className="arb-mono" style={{ fontSize: 11, color: tok.paperDim, background: tok.panelRaised, border: `1px solid ${tok.hairlineSoft}`, borderRadius: 4, padding: '3px 7px' }}>{r}</span>)}
                </div>
              )}
              <div className="arb-mono" style={{ fontSize: 11.5, color: tok.paperFaint, display: 'flex', gap: 14, flexWrap: 'wrap' }}>
                <span>#{truncHash(lastResult.hash)}</span><span>{new Date(lastResult.timestamp).toLocaleString()}</span>
              </div>
            </div>
          </Card>
        )}
      </div>

      <Card style={{ padding: 0, overflow: 'hidden', alignSelf: 'start' }}>
        <button onClick={() => setPolicyOpen((v) => !v)} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'transparent', border: 'none', padding: 18, cursor: 'pointer', color: tok.paper }}>
          <span className="arb-ui" style={{ display: 'flex', alignItems: 'center', gap: 9, fontSize: 13.5, fontWeight: 600 }}><Settings2 size={15} color={tok.paperDim} /> Auditor policy</span>
          {policyOpen ? <ChevronDown size={16} color={tok.paperDim} /> : <ChevronRight size={16} color={tok.paperDim} />}
        </button>
        {policyOpen && (
          <div style={{ padding: '0 18px 20px', display: 'flex', flexDirection: 'column', gap: 18, borderTop: `1px solid ${tok.hairlineSoft}` }}>
            <div style={{ marginTop: 18 }}>
              <div className="arb-ui" style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.8, color: tok.paperDim, textTransform: 'uppercase', marginBottom: 8 }}>Compute cap (H100e / run)</div>
              <input type="number" value={policy.computeCap} onChange={(e) => patchPolicy('computeCap', Number(e.target.value))}
                style={{ width: '100%', background: tok.ink, border: `1px solid ${tok.hairline}`, borderRadius: 4, padding: '7px 9px', fontSize: 13, color: tok.paper, fontFamily: 'JetBrains Mono, monospace', boxSizing: 'border-box' }} />
            </div>
            <PolicyListEditor label="Banned techniques" items={policy.bannedTechniques} onChange={(v) => patchPolicy('bannedTechniques', v)} />
            <PolicyListEditor label="Required disclosures" items={policy.requiredTechniques} onChange={(v) => patchPolicy('requiredTechniques', v)} />
            <div>
              <div className="arb-ui" style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.8, color: tok.paperDim, textTransform: 'uppercase', marginBottom: 8 }}>Auditor notes</div>
              <input value={policy.notes} onChange={(e) => patchPolicy('notes', e.target.value)}
                style={{ width: '100%', background: tok.ink, border: `1px solid ${tok.hairline}`, borderRadius: 4, padding: '7px 9px', fontSize: 13, color: tok.paper, fontFamily: 'Inter, sans-serif', boxSizing: 'border-box' }} />
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

/* ============================== TAB: LEDGER ============================== */
function LedgerTab({ ledger, chainStatus, onVerify, onExport, expanded, toggleExpand }) {
  return (
    <Card>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <span className="arb-ui" style={{ display: 'flex', alignItems: 'center', gap: 9, fontSize: 13.5, fontWeight: 600 }}>
          <ScrollText size={15} color={tok.paperDim} /> Unified ledger <span className="arb-mono" style={{ fontSize: 11.5, color: tok.paperFaint }}>({ledger.length})</span>
        </span>
        <div style={{ display: 'flex', gap: 6 }}>
          <SmallBtn onClick={onVerify} disabled={ledger.length === 0} title="Recompute the hash chain client-side"><Link2 size={13.5} /></SmallBtn>
          <SmallBtn onClick={onExport} disabled={ledger.length === 0} title="Export as JSON"><Download size={13.5} /></SmallBtn>
        </div>
      </div>
      {chainStatus && (
        <div className="arb-ui" style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, marginBottom: 12, padding: '7px 10px', borderRadius: 5, background: tok.ink, color: chainStatus === 'ok' ? tok.seal : chainStatus === 'broken' ? tok.oxide : tok.paperDim }}>
          {chainStatus === 'checking' && <RefreshCw size={13} style={{ animation: 'spin 0.8s linear infinite' }} />}
          {chainStatus === 'ok' && <Link2 size={13} />}
          {chainStatus === 'broken' && <AlertCircle size={13} />}
          {chainStatus === 'checking' && 'Recomputing hash chain…'}
          {chainStatus === 'ok' && `Chain intact — all ${ledger.length} entries verify.`}
          {chainStatus === 'broken' && 'Chain broken — an entry does not match its recorded hash.'}
        </div>
      )}
      {ledger.length === 0 ? (
        <div className="arb-ui" style={{ color: tok.paperFaint, fontSize: 13, lineHeight: 1.6, padding: '8px 2px' }}>
          Nothing recorded yet. Register a unit, issue a license, or run a workload review to start the chain.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2, maxHeight: 560, overflowY: 'auto' }}>
          {[...ledger].reverse().map((entry) => {
            const wl = entry.type === 'workload_review' ? DECISION_META[entry.detail.decision] : null;
            const meta = wl || LEDGER_TYPE_META[entry.type] || { icon: ScrollText, color: tok.paperDim, label: entry.type };
            const Icon = meta.icon;
            const isOpen = !!expanded[entry.id];
            return (
              <div key={entry.id} className="arb-row" style={{ borderRadius: 6, padding: '9px 8px', cursor: 'pointer' }} onClick={() => toggleExpand(entry.id)}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Icon size={15} color={meta.color} style={{ flexShrink: 0 }} />
                  <span className="arb-ui" style={{ fontSize: 12, color: tok.paperFaint, flexShrink: 0, fontFamily: 'JetBrains Mono, monospace' }}>{fmtTime(new Date(entry.timestamp).getTime())}</span>
                  <span className="arb-ui" style={{ fontSize: 12.5, color: tok.paper, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>{entry.summary}</span>
                  {isOpen ? <ChevronDown size={13} color={tok.paperFaint} /> : <ChevronRight size={13} color={tok.paperFaint} />}
                </div>
                {isOpen && (
                  <div style={{ marginTop: 10, marginLeft: 25, paddingRight: 6 }}>
                    <pre className="arb-mono" style={{ fontSize: 11, color: tok.paperDim, background: tok.ink, borderRadius: 5, padding: 10, overflowX: 'auto', margin: '0 0 8px', whiteSpace: 'pre-wrap' }}>
                      {JSON.stringify(entry.detail, null, 2)}
                    </pre>
                    <div className="arb-mono" style={{ fontSize: 10.5, color: tok.paperFaint, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                      <span>hash {truncHash(entry.hash)}</span><span>prev {truncHash(entry.prevHash)}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

/* ============================== MAIN APP ============================== */
export default function Arbiter() {
  const [ready, setReady] = useState(false);
  const [activeTab, setActiveTab] = useState('registry');

  const [policy, setPolicyState] = useState(DEFAULT_POLICY);
  const [policyOpen, setPolicyOpen] = useState(false);

  const [unitsState, setUnitsState] = useState([]);
  const unitsRef = useRef([]);

  const [ledgerState, setLedgerState] = useState([]);
  const ledgerRef = useRef([]);

  const [simClock, setSimClockState] = useState(Date.now());
  const simClockRef = useRef(Date.now());

  const [signers, setSigners] = useState([]);
  const [signerFingerprints, setSignerFingerprints] = useState([]);

  const [submission, setSubmission] = useState('');
  const [reviewing, setReviewing] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [error, setError] = useState(null);
  const [selectedUnitId, setSelectedUnitId] = useState('');

  const [auditing, setAuditing] = useState(false);
  const [lastCertificate, setLastCertificate] = useState(null);
  const [busyUnitId, setBusyUnitId] = useState(null);
  const [replayResult, setReplayResult] = useState(null);

  const [chainStatus, setChainStatus] = useState(null);
  const [expanded, setExpanded] = useState({});

  const persist = async (key, value) => { try { await window.storage.set(key, typeof value === 'string' ? value : JSON.stringify(value)); } catch (e) { console.error(e); } };
  const setUnits = (next) => { unitsRef.current = next; setUnitsState(next); persist('arbiter:units', next); };
  const setLedger = (next) => { ledgerRef.current = next; setLedgerState(next); persist('arbiter:ledger', next); };
  const setSimClock = (next) => { simClockRef.current = next; setSimClockState(next); persist('arbiter:simclock', String(next)); };
  const patchPolicy = (field, value) => setPolicyState((prev) => { const next = { ...prev, [field]: value }; persist('arbiter:policy', next); return next; });

  useEffect(() => {
    (async () => {
      try { const p = await window.storage.get('arbiter:policy'); if (p?.value) setPolicyState(JSON.parse(p.value)); } catch (e) {}

      const now = Date.now();
      try {
        const c = await window.storage.get('arbiter:simclock');
        const clock = c?.value ? Number(c.value) : now;
        simClockRef.current = clock; setSimClockState(clock);
      } catch (e) { simClockRef.current = now; setSimClockState(now); }

      try {
        const u = await window.storage.get('arbiter:units');
        if (u?.value) { const parsed = JSON.parse(u.value); unitsRef.current = parsed; setUnitsState(parsed); }
        else { const seeded = buildSeedUnits(simClockRef.current); unitsRef.current = seeded; setUnitsState(seeded); persist('arbiter:units', seeded); }
      } catch (e) { const seeded = buildSeedUnits(simClockRef.current); unitsRef.current = seeded; setUnitsState(seeded); }

      try {
        const l = await window.storage.get('arbiter:ledger');
        if (l?.value) { const parsed = JSON.parse(l.value); ledgerRef.current = parsed; setLedgerState(parsed); }
      } catch (e) {}

      let loadedSigners;
      try {
        const k = await window.storage.get('arbiter:signerkeys');
        if (k?.value) {
          const stored = JSON.parse(k.value);
          loadedSigners = await Promise.all(stored.map(async (s) => ({ id: s.id, name: s.name, ...(await importKeyPairJwk(s.jwk)) })));
        } else {
          loadedSigners = await Promise.all(SIGNER_ROLES.map(async (role) => ({ id: role.id, name: role.name, ...(await generateEcdsaKeyPair()) })));
          const toStore = await Promise.all(loadedSigners.map(async (s) => ({ id: s.id, name: s.name, jwk: await exportKeyPairJwk(s) })));
          persist('arbiter:signerkeys', toStore);
        }
      } catch (e) {
        loadedSigners = await Promise.all(SIGNER_ROLES.map(async (role) => ({ id: role.id, name: role.name, ...(await generateEcdsaKeyPair()) })));
      }
      setSigners(loadedSigners);
      try {
        setSignerFingerprints(await Promise.all(loadedSigners.map(async (s) => ({ id: s.id, name: s.name, fingerprint: await keyFingerprint(s.publicKey) }))));
      } catch (e) {}

      setReady(true);
    })();
  }, []);

  const appendLedger = async (type, summary, detail) => {
    const prevHash = ledgerRef.current.length > 0 ? ledgerRef.current[ledgerRef.current.length - 1].hash : GENESIS;
    const core = { id: genId('ledger'), timestamp: new Date(simClockRef.current).toISOString(), type, summary, detail, prevHash };
    const hash = await sha256Hex(prevHash + JSON.stringify(core));
    const entry = { ...core, hash };
    setLedger([...ledgerRef.current, entry]);
    return entry;
  };

  const addUnit = async (org, declared, trueVal) => {
    const id = genId('unit');
    const unit = { id, org, declaredH100e: declared, trueH100e: trueVal, registeredAt: simClockRef.current, auditStatus: 'unaudited', license: null, licenseHistory: [], pendingProposal: null, revoked: false };
    setUnits([...unitsRef.current, unit]);
    await appendLedger('registry_add', `${org} registered ${fmtNum(declared)} H100e`, { unitId: id, org, declaredH100e: declared });
  };

  const runAudit = async () => {
    setAuditing(true);
    try {
      const result = computeAuditRound(unitsRef.current, THRESHOLD_H100E);
      const flagSet = new Set(result.flaggedIds), sampleSet = new Set(result.sampledIds);
      const next = unitsRef.current.map((u) => {
        if (flagSet.has(u.id)) return { ...u, auditStatus: 'flagged' };
        if (u.declaredH100e >= THRESHOLD_H100E || sampleSet.has(u.id)) return { ...u, auditStatus: 'verified' };
        return u;
      });
      setUnits(next);
      setLastCertificate(result);
      await appendLedger('audit_round', `Audit round: ${result.exhaustiveCount} exhaustive + ${result.tailSampled}/${result.tailTotal} tail sampled, bound ${result.boundPct.toFixed(2)}% of declared`, result);
    } finally { setAuditing(false); }
  };

  const proposeLicense = async (unitId) => {
    setBusyUnitId(unitId);
    try {
      const unit = unitsRef.current.find((u) => u.id === unitId);
      if (!unit || unit.pendingProposal) return;
      const nextSeq = (unit.license?.token?.sequence ?? 0) + 1;
      const issuedAt = simClockRef.current, expiresAt = issuedAt + LICENSE_DURATION_MS;
      const token = { unitId, sequence: nextSeq, issuedAt, expiresAt };
      setUnits(unitsRef.current.map((u) => (u.id === unitId ? { ...u, pendingProposal: { token, signatures: [] } } : u)));
      await appendLedger('license_propose', `${unit.org}: license proposed, sequence #${nextSeq}, awaiting ${QUORUM_THRESHOLD}-of-${signers.length} quorum`, { unitId, org: unit.org, sequence: nextSeq });
    } finally { setBusyUnitId(null); }
  };

  const signProposal = async (unitId, signerId) => {
    setBusyUnitId(unitId);
    try {
      const unit = unitsRef.current.find((u) => u.id === unitId);
      const signer = signers.find((s) => s.id === signerId);
      if (!unit || !unit.pendingProposal || !signer) return;
      if (unit.pendingProposal.signatures.some((sig) => sig.signerId === signerId)) return;
      const signature = await signPayload(signer.privateKey, unit.pendingProposal.token);
      const newSignatures = [...unit.pendingProposal.signatures, { signerId, signature }];
      await appendLedger(
        'license_sign',
        `${unit.org}: ${signer.name} signed sequence #${unit.pendingProposal.token.sequence} (${newSignatures.length}/${QUORUM_THRESHOLD})`,
        { unitId, org: unit.org, signerId, signerName: signer.name, sequence: unit.pendingProposal.token.sequence, progress: `${newSignatures.length}/${QUORUM_THRESHOLD}` }
      );
      if (newSignatures.length >= QUORUM_THRESHOLD) {
        const finalized = { token: unit.pendingProposal.token, signatures: newSignatures };
        const history = unit.license ? [...unit.licenseHistory, unit.license] : unit.licenseHistory;
        setUnits(unitsRef.current.map((u) => (u.id === unitId ? { ...u, license: finalized, licenseHistory: history, pendingProposal: null, revoked: false } : u)));
        await appendLedger('license_finalize', `${unit.org}: quorum reached, license active (sequence #${finalized.token.sequence})`, { unitId, org: unit.org, sequence: finalized.token.sequence, signers: newSignatures.map((s) => s.signerId) });
      } else {
        setUnits(unitsRef.current.map((u) => (u.id === unitId ? { ...u, pendingProposal: { ...u.pendingProposal, signatures: newSignatures } } : u)));
      }
    } finally { setBusyUnitId(null); }
  };

  const revokeLicense = async (unitId) => {
    setBusyUnitId(unitId);
    try {
      const unit = unitsRef.current.find((u) => u.id === unitId);
      if (!unit) return;
      setUnits(unitsRef.current.map((u) => (u.id === unitId ? { ...u, revoked: true } : u)));
      await appendLedger('license_revoke', `${unit.org}: license revoked`, { unitId, org: unit.org });
    } finally { setBusyUnitId(null); }
  };

  const simulateReplay = async (unitId, oldEntry) => {
    if (!oldEntry) return;
    const unit = unitsRef.current.find((u) => u.id === unitId);
    if (!unit) return;
    let validSignatures = 0;
    for (const sig of oldEntry.signatures) {
      const signer = signers.find((s) => s.id === sig.signerId);
      if (signer && (await verifyPayload(signer.publicKey, oldEntry.token, sig.signature))) validSignatures++;
    }
    const currentSeq = unit.license?.token?.sequence ?? 0;
    const accepted = validSignatures >= QUORUM_THRESHOLD && oldEntry.token.sequence === currentSeq;
    const result = { unitId, org: unit.org, attemptedSequence: oldEntry.token.sequence, currentSequence: currentSeq, validSignatures, totalSignatures: oldEntry.signatures.length, accepted };
    setReplayResult(result);
    await appendLedger(
      accepted ? 'license_finalize' : 'license_replay_blocked',
      accepted ? `${unit.org}: presented token accepted` : `${unit.org}: replay of sequence #${oldEntry.token.sequence} blocked (${validSignatures}/${oldEntry.signatures.length} signatures valid, current is #${currentSeq})`,
      result
    );
  };

  const runReview = async () => {
    if (!submission.trim() || reviewing) return;
    setReviewing(true); setError(null); setLastResult(null);
    const unit = selectedUnitId ? unitsRef.current.find((u) => u.id === selectedUnitId) : null;
    try {
      if (unit) {
        const status = computeLicenseStatus(unit, simClockRef.current);
        if (status === 'none' || status === 'revoked' || status === 'expired') {
          const entry = await appendLedger('workload_review', `${unit.org}: auto-rejected — license status "${status}"`, {
            unitId: unit.id, org: unit.org, decision: 'rejected', riskTier: 'high', confidence: 1,
            reasoning: `This unit's license status is "${status}." Workloads cannot be authorized on compute without an active license, regardless of what the submission says.`,
            triggeredRules: ['no active license'],
          });
          setLastResult(entry); setReviewing(false); return;
        }
      }
      const systemPrompt = `You are the automated first-pass reviewer in an AI workload approval pipeline, modeled on the "workload approval" step in the AI Futures Project's AI 2040 Plan A verification architecture. Auditors currently do this manually; you are a first-pass copilot that triages submissions before a human sees them, not a final authority.

CURRENT POLICY
- Compute cap: ${policy.computeCap} H100e-equivalent per run
- Banned: ${policy.bannedTechniques.filter(Boolean).join('; ') || '(none configured)'}
- Required disclosures: ${policy.requiredTechniques.filter(Boolean).join('; ') || '(none configured)'}
- Auditor notes: ${policy.notes || '(none)'}
${unit ? `\nThis submission is running on a registered unit: ${unit.org}, declared ${unit.declaredH100e} H100e, audit status "${unit.auditStatus}."` : ''}

Review the workload submission below against this policy. Be a careful, skeptical auditor: treat vagueness or a missing required disclosure as at least "flagged," and reject anything matching a banned item. risk_tier should reflect how dangerous the workload would be if the stated facts turn out to be misleading, per Plan A's Extreme/High/Lower risk tiering.

Respond with ONLY raw JSON, no markdown fences, no commentary, matching exactly:
{"decision":"approved|flagged|rejected","risk_tier":"lower|high|extreme","confidence":0.0,"reasoning":"2-3 sentences","triggered_rules":["short phrase","..."]}`;

      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 1000, system: systemPrompt, messages: [{ role: 'user', content: `WORKLOAD SUBMISSION:\n${submission}` }] }),
      });
      const data = await response.json();
      const raw = (data.content || []).map((b) => b.text || '').join('\n');
      const parsed = JSON.parse(raw.replace(/```json|```/g, '').trim());
      if (!DECISION_META[parsed.decision]) throw new Error('bad decision field');

      const entry = await appendLedger('workload_review', `${unit ? unit.org + ': ' : ''}workload ${parsed.decision}`, {
        unitId: unit ? unit.id : null, org: unit ? unit.org : null, decision: parsed.decision, riskTier: parsed.risk_tier,
        confidence: parsed.confidence, reasoning: parsed.reasoning, triggeredRules: Array.isArray(parsed.triggered_rules) ? parsed.triggered_rules : [],
        workloadExcerpt: submission.slice(0, 320),
      });
      setLastResult(entry); setSubmission('');
    } catch (e) {
      console.error(e);
      setError("The review call didn't come back cleanly — try again.");
    } finally { setReviewing(false); }
  };

  const verifyChain = async () => {
    setChainStatus('checking');
    let prevHash = GENESIS;
    for (const entry of ledgerRef.current) {
      if (entry.prevHash !== prevHash) { setChainStatus('broken'); return; }
      const { hash, ...core } = entry;
      const recomputed = await sha256Hex(entry.prevHash + JSON.stringify(core));
      if (recomputed !== hash) { setChainStatus('broken'); return; }
      prevHash = hash;
    }
    await new Promise((r) => setTimeout(r, 300));
    setChainStatus('ok');
  };

  const exportLedger = () => {
    const blob = new Blob([JSON.stringify(ledgerRef.current, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'arbiter-ledger.json'; a.click();
    URL.revokeObjectURL(url);
  };

  const toggleExpand = (id) => setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));

  return (
    <div style={{ background: tok.ink, minHeight: '100vh', color: tok.paper }} className="w-full">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        .arb-serif { font-family: 'Source Serif 4', Georgia, serif; }
        .arb-ui { font-family: 'Inter', system-ui, sans-serif; }
        .arb-mono { font-family: 'JetBrains Mono', monospace; }
        .arb-textarea::placeholder { color: ${tok.paperFaint}; }
        .arb-btn-primary:disabled { opacity: 0.5; cursor: default; }
        .arb-btn-primary:not(:disabled):hover { filter: brightness(1.12); }
        .arb-example:hover { border-color: ${tok.paperDim} !important; }
        .arb-row:hover { background: ${tok.panelRaised}; }
        select { color-scheme: dark; }
        ::selection { background: ${tok.seal}55; }
        @keyframes spin { to { transform: rotate(360deg); } }
        @media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
      `}</style>

      <div style={{ maxWidth: 1180, margin: '0 auto', padding: '52px 24px 80px' }}>
        <div style={{ marginBottom: 8, paddingBottom: 28 }}>
          <div className="arb-ui" style={{ fontSize: 11.5, fontWeight: 600, letterSpacing: 2, color: tok.seal, textTransform: 'uppercase', marginBottom: 12 }}>AI 2040 · Plan A · Compute Governance Lifecycle</div>
          <h1 className="arb-serif" style={{ fontSize: 42, fontWeight: 600, margin: 0, lineHeight: 1.1, letterSpacing: -0.5 }}>Arbiter</h1>
          <p className="arb-ui" style={{ maxWidth: 680, color: tok.paperDim, fontSize: 14.5, lineHeight: 1.6, marginTop: 14 }}>
            Register a compute unit, keep it under an active cryptographic license, and review what it actually runs
            against policy — all three writing into one hash-chained ledger, so nothing about the history can be
            edited quietly.
          </p>
        </div>

        <div style={{ display: 'flex', gap: 4, borderBottom: `1px solid ${tok.hairline}`, marginBottom: 28, overflowX: 'auto' }}>
          <TabButton active={activeTab === 'registry'} onClick={() => setActiveTab('registry')} icon={Building2} label="Registry" count={unitsState.length} />
          <TabButton active={activeTab === 'licensing'} onClick={() => setActiveTab('licensing')} icon={KeyRound} label="Licensing" />
          <TabButton active={activeTab === 'workloads'} onClick={() => setActiveTab('workloads')} icon={ClipboardCheck} label="Workloads" />
          <TabButton active={activeTab === 'ledger'} onClick={() => setActiveTab('ledger')} icon={ScrollText} label="Ledger" count={ledgerState.length} />
        </div>

        {!ready ? (
          <div className="arb-ui" style={{ color: tok.paperFaint, fontSize: 13 }}>Loading…</div>
        ) : (
          <>
            {activeTab === 'registry' && <RegistryTab units={unitsState} lastCertificate={lastCertificate} onAddUnit={addUnit} onRunAudit={runAudit} auditing={auditing} />}
            {activeTab === 'licensing' && <LicensingTab units={unitsState} simClock={simClock} signerFingerprints={signerFingerprints} onPropose={proposeLicense} onSign={signProposal} onRevoke={revokeLicense} onSimulateReplay={simulateReplay} replayResult={replayResult} busyUnitId={busyUnitId} onAdvanceClock={(ms) => setSimClock(simClockRef.current + ms)} />}
            {activeTab === 'workloads' && <WorkloadsTab units={unitsState} policy={policy} policyOpen={policyOpen} setPolicyOpen={setPolicyOpen} patchPolicy={patchPolicy} submission={submission} setSubmission={setSubmission} reviewing={reviewing} lastResult={lastResult} error={error} onSubmit={runReview} selectedUnitId={selectedUnitId} setSelectedUnitId={setSelectedUnitId} />}
            {activeTab === 'ledger' && <LedgerTab ledger={ledgerState} chainStatus={chainStatus} onVerify={verifyChain} onExport={exportLedger} expanded={expanded} toggleExpand={toggleExpand} />}
          </>
        )}

        <div style={{ marginTop: 48, paddingTop: 24, borderTop: `1px solid ${tok.hairline}` }} className="arb-ui">
          <p style={{ fontSize: 12.5, color: tok.paperFaint, lineHeight: 1.7, maxWidth: 820 }}>
            The signing, verification, hashing, and statistics here are real — generated in your browser via Web
            Crypto, not mocked, including genuine k-of-{signers.length || 5} quorum signing: a license needs {QUORUM_THRESHOLD}
            {' '}independent signers, not one authority. What's still a stand-in for a production system: browser
            storage rather than a real backend, and a simulated clock. The registry's "true" values are only
            knowable here because this is a demo; in the field that's exactly the fact a physical audit exists to
            establish.
          </p>
        </div>
      </div>
    </div>
  );
}
