import { useState, type FormEvent, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { Link, Route, Switch, useLocation, useParams, Router as WouterRouter } from 'wouter';
import {
  Activity, ArrowDownLeft, ArrowLeft, ArrowRight, Check, ChevronLeft, ChevronRight,
  CircleAlert, Clock3, FileSearch, Fingerprint, Gauge, Globe2,
  LockKeyhole, LogOut, Mail, Menu, MessageSquareText, Search, Settings2, Shield,
  ShieldAlert, ShieldCheck, Trash2, TriangleAlert, X,
} from 'lucide-react';
import {
  getGetCurrentUserQueryKey, getGetDashboardStatsQueryKey, getGetScanQueryKey,
  getListScansQueryKey, useCreateCombinedScan, useCreateFeedback, useCreateTextScan,
  useCreateUrlScan, useDeleteScan, useGetCurrentUser, useGetDashboardStats,
  useGetScan, useHealthCheck, useListScans, useLogin, useLogout, useRegister,
} from '@workspace/api-client-react';
import type { Scan, Verdict } from '@workspace/api-client-react';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';

const queryClient = new QueryClient();

const navItems = [
  { href: '/dashboard', label: 'Overview', icon: Gauge },
  { href: '/scan', label: 'New check', icon: Search },
  { href: '/history', label: 'Scan history', icon: Clock3 },
  { href: '/settings', label: 'Privacy & method', icon: Settings2 },
];

function Brand({ compact = false }: { compact?: boolean }) {
  return <Link href="/" className={`brand ${compact ? 'brand-compact' : ''}`} data-testid="link-brand-home">
    <span className="brand-symbol"><Shield size={20} strokeWidth={2.1} /></span>
    {!compact && <span>scam<span className="brand-light">shield</span><small>AI</small></span>}
  </Link>;
}

function Shell({ children }: { children: ReactNode }) {
  const [location, setLocation] = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const current = useGetCurrentUser();
  const logout = useLogout();
  const client = useQueryClient();
  const user = current.data?.user ?? null;
  const signedIn = Boolean(user);
  const logoutNow = () => logout.mutate(undefined, {
    onSuccess: () => {
      client.setQueryData(getGetCurrentUserQueryKey(), { user: null });
      setLocation('/');
    },
  });
  const isAuth = location === '/login' || location === '/register';
  if (location === '/' || isAuth) return <>{children}</>;
  return <div className="app-frame">
    <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
      <div className="sidebar-top"><Brand /><button className="icon-button mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close menu" data-testid="button-close-menu"><X size={18} /></button></div>
      <div className="workspace-label">YOUR WORKSPACE</div>
      <nav className="side-nav" aria-label="Main navigation">
        {navItems.map(({ href, label, icon: Icon }) => <Link key={href} href={href} className={`nav-link ${location === href || (href === '/dashboard' && location === '/') ? 'nav-active' : ''}`} onClick={() => setMobileOpen(false)} data-testid={`link-nav-${href.slice(1)}`}>
          <Icon size={17} strokeWidth={1.8} /><span>{label}</span>{href === '/scan' && <span className="nav-key">+</span>}
        </Link>)}
      </nav>
      <div className="sidebar-note">
        <div className="sidebar-note-mark"><ShieldCheck size={17} /></div>
        <p>Pause before you tap.</p>
        <span>Evidence can guide a decision, but no check can guarantee safety.</span>
      </div>
      <div className="sidebar-bottom">
        {signedIn ? <div className="profile-row">
          <div className="initial-avatar">{user?.name?.slice(0, 1)?.toUpperCase() || 'U'}</div>
          <div className="profile-copy"><strong data-testid="text-account-name">{user?.name}</strong><span>{user?.email}</span></div>
          <button onClick={logoutNow} className="icon-button logout-button" aria-label="Sign out" disabled={logout.isPending} data-testid="button-sign-out"><LogOut size={16} /></button>
        </div> : <div className="sidebar-auth"><Link href="/login" data-testid="link-sidebar-login">Sign in</Link><Link href="/register" data-testid="link-sidebar-register">Create account <ArrowRight size={14} /></Link></div>}
      </div>
    </aside>
    {mobileOpen && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} data-testid="button-navigation-scrim" />}
    <div className="main-column">
      <header className="topbar">
        <button className="icon-button mobile-menu" aria-label="Open menu" onClick={() => setMobileOpen(true)} data-testid="button-open-menu"><Menu size={19} /></button>
        <div className="breadcrumb"><span>ScamShield</span><span className="crumb-sep">/</span><span>{navItems.find(i => i.href === location)?.label || 'Scan detail'}</span></div>
        <div className="topbar-status"><span className="status-dot" /> Private session <LockKeyhole size={13} /></div>
      </header>
      <main className="main-content">{children}</main>
    </div>
  </div>;
}

function Landing() {
  const health = useHealthCheck();
  const current = useGetCurrentUser();
  const accountHref = current.data?.user ? '/dashboard' : '/register';
  return <div className="landing">
    <header className="landing-header">
      <Brand />
      <nav className="landing-nav">
        <a href="#how-it-works" data-testid="link-how-it-works">How it works</a>
        <a href="#principles" data-testid="link-principles">Our principles</a>
      </nav>
      <div className="landing-actions"><Link href="/login" className="text-link" data-testid="link-landing-login">Sign in</Link><Link href={accountHref} className="button button-dark button-small" data-testid="link-landing-start">Open ScamShield <ArrowRight size={15} /></Link></div>
    </header>
    <section className="hero">
      <div className="hero-grid" />
      <div className="hero-copy">
        <div className="eyebrow"><span className="eyebrow-line" /> A second opinion for the internet</div>
        <h1>That message<br />can <em>wait.</em></h1>
        <p className="hero-lede">Check a suspicious link or message before you act. Get a clear read on the signals, with the evidence and uncertainty left in plain sight.</p>
        <div className="hero-ctas"><Link href="/scan" className="button button-green" data-testid="link-hero-scan"><Search size={16} /> Check something suspicious <ArrowRight size={16} /></Link><Link href="/dashboard" className="hero-secondary" data-testid="link-hero-dashboard">Go to my account <ArrowRight size={15} /></Link></div>
        <div className="hero-assurance"><LockKeyhole size={14} /><span>Your checks are private to your account.</span><span className="assurance-divider" /> No link is opened by the checker.</div>
        <div className={`service-health ${health.isError ? 'health-offline' : ''}`} data-testid="status-service-health"><span className="status-dot" />{health.isLoading ? 'Checking service status' : health.isError ? 'Service status unavailable' : health.data?.status ? `Checker status: ${health.data.status}` : 'Service responded'}</div>
      </div>
      <div className="hero-visual" aria-label="Illustration of a careful message review">
        <div className="visual-orbit orbit-one" /><div className="visual-orbit orbit-two" />
        <div className="visual-kicker"><span className="mini-pulse" /> INPUT YOU CAN CHECK <span>ILLUSTRATION</span></div>
        <div className="message-card">
          <div className="message-top"><span className="sender-icon"><Mail size={16} /></span><div><b>Message preview</b><small>illustrative input only</small></div><FileSearch size={16} className="message-alert" /></div>
          <div className="message-body">Your parcel is waiting.<br />Review delivery details at the<br />address below.</div>
          <div className="message-link"><span>delivery-example.test</span><ArrowDownLeft size={15} /></div>
          <div className="review-rule" />
          <div className="review-caption"><ShieldCheck size={16} /><span>Example input only — not a scan result.</span></div>
        </div>
        <div className="floating-stamp"><Fingerprint size={17} /><span>PAUSE<br />BEFORE TAPPING</span></div>
        <div className="visual-foot"><span>NO RESULT IS SHOWN</span><span>SCAMSHIELD / FIELD NOTE 001</span></div>
      </div>
      <div className="hero-index">01 <span>/</span> 04</div>
    </section>
    <section className="principles-strip" id="principles">
      <div><span className="strip-number">01</span><div><strong>Evidence, not a verdict from nowhere.</strong><p>See the signals behind each assessment.</p></div></div>
      <div><span className="strip-number">02</span><div><strong>Cautious by design.</strong><p>Uncertainty stays visible. Nothing is called guaranteed safe.</p></div></div>
      <div><span className="strip-number">03</span><div><strong>You choose what to do next.</strong><p>Practical guidance, never pressure.</p></div></div>
    </section>
    <section className="how-section" id="how-it-works">
      <div className="section-overline">A useful pause, in three steps <span>02 — PROCESS</span></div>
      <div className="how-heading"><h2>Look at the clues.<br /><em>Then decide.</em></h2><p>ScamShield helps you inspect what arrived, without making the decision for you.</p></div>
      <div className="steps">
        <article className="step"><span className="step-index">01 / SUBMIT</span><div className="step-icon"><MessageSquareText size={20} /></div><h3>Bring the message.</h3><p>Paste a URL, a message, or both. You do not need to open a link to check it.</p></article>
        <article className="step"><span className="step-index">02 / REVIEW</span><div className="step-icon"><FileSearch size={20} /></div><h3>Read the signals.</h3><p>Review the assessment alongside specific indicators, recommendations, and limitations.</p></article>
        <article className="step"><span className="step-index">03 / CHOOSE</span><div className="step-icon"><ShieldCheck size={20} /></div><h3>Take a measured next step.</h3><p>Use what you learned to verify through a trusted channel—or simply leave it alone.</p></article>
      </div>
    </section>
    <section className="landing-caution">
      <div className="caution-mark"><TriangleAlert size={24} /></div>
      <div><span className="section-overline">A note on certainty</span><h2>A lower-risk signal<br />is not a clean bill of health.</h2></div>
      <p>Threats change, context matters, and automated checks have limits. ScamShield is one useful input—not a substitute for verifying with the person or organization through a channel you already trust.</p>
      <Link href="/settings" className="text-link" data-testid="link-landing-methodology">Read how we assess <ArrowRight size={15} /></Link>
    </section>
    <footer className="landing-footer"><Brand /><span>Stay curious. Stay cautious.</span><div><Link href="/settings" data-testid="link-footer-privacy">Privacy & methodology</Link><Link href="/login" data-testid="link-footer-account">Your account</Link></div><small>© ScamShield AI</small></footer>
  </div>;
}

function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow page-eyebrow"><span className="eyebrow-line" />{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action && <div className="heading-action">{action}</div>}</div>;
}

function LoadingBlock({ label = 'Loading your account data' }: { label?: string }) {
  return <div className="loading-state" role="status" data-testid="status-loading"><div className="skeleton-line skeleton-short" /><div className="skeleton-line" /><span>{label}</span></div>;
}

function QueryError({ retry, message = 'We could not load this information right now.' }: { retry: () => void; message?: string }) {
  return <div className="error-panel" role="alert" data-testid="status-api-error"><CircleAlert size={19} /><div><strong>Something did not load.</strong><p>{message}</p></div><button className="button button-outline button-small" onClick={retry} data-testid="button-retry">Try again</button></div>;
}

function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return <span className={`verdict-badge verdict-${verdict}`} data-testid={`status-verdict-${verdict}`}><span className="verdict-dot" />{verdict.replace('-', ' ')}</span>;
}

function RiskMeter({ score }: { score: number }) {
  return <div className="risk-meter" aria-label={`Risk score ${score} out of 100`} data-testid="meter-risk-score"><div className="risk-track"><span style={{ width: `${Math.min(100, Math.max(0, score))}%` }} /></div><span className="risk-value">{score}<small>/100</small></span></div>;
}

function formatDate(value: string, includeTime = false) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, includeTime ? { dateStyle: 'medium', timeStyle: 'short' } : { dateStyle: 'medium' }).format(date);
}

function ScanRow({ scan }: { scan: Scan }) {
  return <Link href={`/scans/${scan.id}`} className="scan-row" data-testid={`link-scan-${scan.id}`}>
    <div className={`scan-type-icon type-${scan.inputType}`}><ScanTypeIcon type={scan.inputType} /></div>
    <div className="scan-row-main"><strong>{scan.redactedPreview || `${scan.inputType} check`}</strong><span>{scan.inputType} · {formatDate(scan.createdAt, true)}</span></div>
    <VerdictBadge verdict={scan.verdict} /><div className="scan-row-score"><span>Risk</span><b>{scan.riskScore}</b></div><ArrowRight className="row-arrow" size={16} />
  </Link>;
}

function ScanTypeIcon({ type }: { type: string }) {
  if (type === 'url') return <Globe2 size={17} />;
  if (type === 'combined') return <MessageSquareText size={17} />;
  return <FileSearch size={17} />;
}

function Dashboard() {
  const current = useGetCurrentUser();
  const statsQuery = useGetDashboardStats({ days: 30 }, { query: { queryKey: getGetDashboardStatsQueryKey({ days: 30 }), enabled: Boolean(current.data?.user) } });
  const stats = statsQuery.data;
  if (current.isLoading) return <LoadingBlock />;
  if (!current.data?.user) return <SignInPrompt title="Your account overview" text="Sign in to see your own scan activity. No sample analytics are shown here." />;
  return <div className="page-wrap">
    <PageHeading eyebrow="ACCOUNT OVERVIEW" title={`Good to see you, ${current.data.user.name.split(' ')[0]}.`} description="A grounded view of the checks in your account. No activity is invented or filled in." action={<Link href="/scan" className="button button-green" data-testid="link-dashboard-new-scan"><Search size={16} /> New check <ArrowRight size={15} /></Link>} />
    {current.isError && <QueryError retry={() => current.refetch()} message="Your account session could not be confirmed." />}
    {statsQuery.isLoading && <LoadingBlock label="Loading your scan summary" />}
    {statsQuery.isError && <QueryError retry={() => statsQuery.refetch()} message="We could not retrieve your scan summary." />}
    {stats && <>
      <div className="stats-intro"><span><Activity size={15} /> LAST 30 DAYS</span><span>Based on scans in your account</span></div>
      <section className="stats-grid" aria-label="Scan summary">
        <StatCard label="All checks" value={stats.total} accent="stat-ink" icon={<FileSearch size={17} />} />
        <StatCard label="High risk" value={stats.highRisk} accent="stat-red" icon={<ShieldAlert size={17} />} />
        <StatCard label="Suspicious" value={stats.suspicious} accent="stat-amber" icon={<TriangleAlert size={17} />} />
        <StatCard label="Uncertain" value={stats.uncertain} accent="stat-blue" icon={<CircleAlert size={17} />} />
      </section>
      <div className="dashboard-grid">
        <section className="panel activity-panel">
          <div className="panel-heading"><div><span className="section-overline">YOUR ACTIVITY</span><h2>Checks over time</h2></div><span className="small-pill">30 days</span></div>
          {stats.trend.length ? <TrendChart values={stats.trend} /> : <EmptyInline title="No activity in this period" copy="Your scan timeline will appear here after you run a check." />}
        </section>
        <section className="panel breakdown-panel">
          <div className="panel-heading"><div><span className="section-overline">ASSESSMENTS</span><h2>Verdict mix</h2></div></div>
          <div className="verdict-list">
            {[
              ['high-risk', 'High risk', stats.highRisk],
              ['suspicious', 'Suspicious', stats.suspicious],
              ['uncertain', 'Uncertain', stats.uncertain],
              ['lower-risk', 'Lower risk', stats.lowerRisk],
            ].map(([key, label, count]) => <div className="verdict-line" key={key}><VerdictBadge verdict={key as Verdict} /><span>{count}</span></div>)}
          </div>
          <p className="fine-print">Assessments are signals—not guarantees.</p>
        </section>
      </div>
      <section className="panel recent-panel">
        <div className="panel-heading"><div><span className="section-overline">RECENT ACTIVITY</span><h2>Latest checks</h2></div><Link href="/history" className="text-link" data-testid="link-dashboard-history">All history <ArrowRight size={15} /></Link></div>
        {stats.recent.length ? <div className="scan-list">{stats.recent.slice(0, 5).map(scan => <ScanRow scan={scan} key={scan.id} />)}</div> : <EmptyInline title="Nothing checked yet" copy="Run your first check whenever something does not feel right." link={<Link href="/scan" className="text-link" data-testid="link-dashboard-first-scan">Start a check <ArrowRight size={14} /></Link>} />}
      </section>
    </>}
  </div>;
}

function StatCard({ label, value, accent, icon }: { label: string; value: number; accent: string; icon: ReactNode }) {
  return <article className={`stat-card ${accent}`}><div className="stat-top">{icon}<span>30D</span></div><strong data-testid={`value-stat-${label.toLowerCase().replaceAll(' ', '-')}`}>{value}</strong><span>{label}</span></article>;
}

function TrendChart({ values }: { values: { date: string; count: number }[] }) {
  const max = Math.max(1, ...values.map(value => value.count));
  return <div className="trend-wrap"><div className="trend-chart" data-testid="chart-scan-trend">
    {values.map((item, i) => <div key={`${item.date}-${i}`} className="trend-column" title={`${formatDate(item.date)}: ${item.count} checks`}><span style={{ height: `${Math.max(4, item.count / max * 100)}%` }} /><small>{i % Math.max(1, Math.ceil(values.length / 7)) === 0 ? new Date(item.date).toLocaleDateString(undefined, { day: 'numeric' }) : ''}</small></div>)}
  </div><div className="chart-axis"><span>{values[0] ? formatDate(values[0].date) : ''}</span><span>{values.length ? formatDate(values[values.length - 1].date) : ''}</span></div></div>;
}

function EmptyInline({ title, copy, link }: { title: string; copy: string; link?: ReactNode }) {
  return <div className="empty-inline" data-testid="state-empty"><span className="empty-mark"><Shield size={18} /></span><strong>{title}</strong><p>{copy}</p>{link}</div>;
}

function SignInPrompt({ title, text }: { title: string; text: string }) {
  return <div className="signed-out-panel"><div className="signed-out-icon"><LockKeyhole size={21} /></div><div><span className="section-overline">ACCOUNT REQUIRED</span><h2>{title}</h2><p>{text}</p><div className="signed-out-actions"><Link href="/login" className="button button-green" data-testid="link-prompt-login">Sign in <ArrowRight size={15} /></Link><Link href="/register" className="text-link" data-testid="link-prompt-register">Create an account</Link></div></div></div>;
}

function ScanPage() {
  const [kind, setKind] = useState<'url' | 'text' | 'combined'>('url');
  const [url, setUrl] = useState('');
  const [text, setText] = useState('');
  const urlScan = useCreateUrlScan();
  const textScan = useCreateTextScan();
  const combinedScan = useCreateCombinedScan();
  const current = useGetCurrentUser();
  const [, setLocation] = useLocation();
  const pending = urlScan.isPending || textScan.isPending || combinedScan.isPending;
  const error = urlScan.error || textScan.error || combinedScan.error;
  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const onSuccess = (scan: Scan) => setLocation(`/scans/${scan.id}`);
    if (kind === 'url') urlScan.mutate({ data: { url: url.trim() } }, { onSuccess });
    if (kind === 'text') textScan.mutate({ data: { text: text.trim() } }, { onSuccess });
    if (kind === 'combined') combinedScan.mutate({ data: { text: text.trim() } }, { onSuccess });
  };
  const modes = [
    { id: 'url' as const, label: 'A link', icon: Globe2, subtitle: 'Check a URL without opening it' },
    { id: 'text' as const, label: 'A message', icon: MessageSquareText, subtitle: 'Review wording and context' },
    { id: 'combined' as const, label: 'Both together', icon: Fingerprint, subtitle: 'Message plus any embedded links' },
  ];
  return <div className="page-wrap scan-page">
    <PageHeading eyebrow="CHECK SOMETHING" title="Take a closer look." description="Paste what you received. We will show the signals we can find—and where the assessment has limits." />
    {!current.isLoading && !current.data?.user && <div className="inline-notice"><LockKeyhole size={16} /><span>You can check without signing in, but this scan will not be saved to an account.</span><Link href="/login" data-testid="link-scan-sign-in">Sign in</Link></div>}
    <div className="scan-workspace">
      <section className="scan-form-panel">
        <div className="mode-tabs" role="tablist" aria-label="What would you like to check?">
          {modes.map(({ id, label, icon: Icon }) => <button key={id} role="tab" aria-selected={kind === id} className={`mode-tab ${kind === id ? 'mode-active' : ''}`} onClick={() => setKind(id)} data-testid={`button-mode-${id}`}><Icon size={17} /><span>{label}</span></button>)}
        </div>
        <form onSubmit={handleSubmit}>
          {kind === 'url' ? <div className="input-block"><label htmlFor="scan-url">Suspicious link</label><p>We assess the address itself. The destination will not be opened.</p><div className="url-input-wrap"><Globe2 size={16} /><input id="scan-url" type="url" maxLength={2048} required value={url} onChange={e => setUrl(e.target.value)} placeholder="https://example.com/verify" data-testid="input-scan-url" /></div></div> : <div className="input-block"><label htmlFor="scan-text">{kind === 'combined' ? 'Message and any links inside it' : 'Suspicious message'}</label><p>{kind === 'combined' ? 'Embedded URLs are assessed as part of the message check.' : 'Paste the message as received, including sender wording if useful.'}</p><textarea id="scan-text" value={text} required maxLength={20000} onChange={e => setText(e.target.value)} placeholder="Paste the message here. Example input: “Your parcel is held. Confirm your details at [link] within 24 hours.”" data-testid="input-scan-text" /><div className="textarea-meta"><span>Input only — this is not an assessment example.</span><span>{text.length.toLocaleString()} / 20,000</span></div></div>}
          <div className="privacy-line"><LockKeyhole size={14} /><span>Your submitted content is handled according to the account and privacy policy.</span></div>
          <button className="button button-green scan-submit" type="submit" disabled={pending || (kind === 'url' ? !url.trim() : !text.trim())} data-testid="button-submit-scan">
            {pending ? <><span className="button-pulse" /> Reviewing signals…</> : <><Search size={16} /> Review this {kind === 'url' ? 'link' : kind === 'text' ? 'message' : 'message and links'} <ArrowRight size={15} /></>}
          </button>
          {error && <div className="form-error" role="alert" data-testid="status-scan-error"><CircleAlert size={16} /> The check could not be completed. Please review the input and try again.</div>}
        </form>
      </section>
      <aside className="scan-side">
        <div className="scan-side-heading"><span className="side-emblem"><ShieldCheck size={18} /></span><span>What to expect</span></div>
        <div className="expect-row"><span>01</span><p>Specific indicators will explain why something may deserve attention.</p></div>
        <div className="expect-row"><span>02</span><p>Some checks may be uncertain when there is not enough evidence.</p></div>
        <div className="expect-row"><span>03</span><p>A lower-risk result never means a link is guaranteed safe.</p></div>
        <div className="scan-side-note"><TriangleAlert size={16} /><p>Never share passwords, one-time codes, or financial details with a message you do not trust.</p></div>
      </aside>
    </div>
  </div>;
}

function HistoryPage() {
  const current = useGetCurrentUser();
  const [page, setPage] = useState(1);
  const params = { page, limit: 10 };
  const history = useListScans(params, { query: { queryKey: getListScansQueryKey(params), enabled: Boolean(current.data?.user) } });
  const totalPages = history.data ? Math.max(1, Math.ceil(history.data.total / history.data.limit)) : 1;
  if (current.isLoading) return <LoadingBlock />;
  if (!current.data?.user) return <div className="page-wrap"><PageHeading eyebrow="YOUR RECORD" title="Scan history" description="A real record of checks saved to your account." /><SignInPrompt title="Your checks, in one place." text="Sign in to view saved scan history. This page never fills in example or placeholder scans." /></div>;
  return <div className="page-wrap">
    <PageHeading eyebrow="YOUR RECORD" title="Scan history" description="A real record of checks saved to your account." action={<Link href="/scan" className="button button-green" data-testid="link-history-new-scan"><Search size={16} /> New check</Link>} />
    {history.isLoading && <LoadingBlock label="Loading scan history" />}
    {history.isError && <QueryError retry={() => history.refetch()} message="Your saved checks could not be retrieved." />}
    {history.data && <section className="panel history-panel">
      <div className="history-toolbar"><div><span className="section-overline">SAVED CHECKS</span><strong data-testid="text-history-count">{history.data.total} {history.data.total === 1 ? 'check' : 'checks'}</strong></div><span className="small-pill">Page {history.data.page} of {totalPages}</span></div>
      {history.data.items.length ? <>
        <div className="scan-list">{history.data.items.map(scan => <ScanRow scan={scan} key={scan.id} />)}</div>
        <div className="pagination"><span>Showing {Math.min((page - 1) * history.data.limit + 1, history.data.total)}–{Math.min(page * history.data.limit, history.data.total)} of {history.data.total}</span><div><button className="icon-button" onClick={() => setPage(n => Math.max(1, n - 1))} disabled={page <= 1} aria-label="Previous page" data-testid="button-history-previous"><ChevronLeft size={17} /></button><span data-testid="text-history-page">{page}</span><button className="icon-button" onClick={() => setPage(n => Math.min(totalPages, n + 1))} disabled={page >= totalPages} aria-label="Next page" data-testid="button-history-next"><ChevronRight size={17} /></button></div></div>
      </> : <EmptyInline title="No saved checks yet" copy="When you run a check while signed in, it will appear here." link={<Link href="/scan" className="text-link" data-testid="link-history-first-scan">Run your first check <ArrowRight size={14} /></Link>} />}
    </section>}
  </div>;
}

function ScanDetail() {
  const params = useParams<{ id: string }>();
  const id = params.id || '';
  const scanQuery = useGetScan(id, { query: { queryKey: getGetScanQueryKey(id), enabled: Boolean(id) } });
  const current = useGetCurrentUser();
  const feedback = useCreateFeedback();
  const deleteScan = useDeleteScan();
  const client = useQueryClient();
  const [, setLocation] = useLocation();
  const [feedbackSent, setFeedbackSent] = useState(false);
  const onDelete = () => {
    if (!window.confirm('Delete this saved check? This cannot be undone.')) return;
    deleteScan.mutate({ id }, { onSuccess: () => {
      client.invalidateQueries({ queryKey: getListScansQueryKey() });
      client.invalidateQueries({ queryKey: getGetDashboardStatsQueryKey({ days: 30 }) });
      setLocation('/history');
    } });
  };
  const sendFeedback = (category: 'correct' | 'false-positive' | 'false-negative' | 'other') => feedback.mutate({ data: { scanId: id, category } }, { onSuccess: () => setFeedbackSent(true) });
  if (scanQuery.isLoading) return <LoadingBlock label="Loading scan details" />;
  if (scanQuery.isError) return <div className="page-wrap"><Link href="/history" className="back-link" data-testid="link-detail-back"><ArrowLeft size={15} /> Back to history</Link><QueryError retry={() => scanQuery.refetch()} message="This scan could not be found or is no longer available." /></div>;
  const scan = scanQuery.data;
  if (!scan) return null;
  return <div className="page-wrap detail-page">
    <Link href="/history" className="back-link" data-testid="link-detail-back"><ArrowLeft size={15} /> Back to history</Link>
    <PageHeading eyebrow={`${scan.inputType.toUpperCase()} REVIEW · ${formatDate(scan.createdAt, true)}`} title="Assessment details" description="Review the recorded signals and their limitations before deciding what to do next." action={current.data?.user ? <button className="button button-outline button-small button-delete" onClick={onDelete} disabled={deleteScan.isPending} data-testid="button-delete-scan"><Trash2 size={15} /> {deleteScan.isPending ? 'Deleting…' : 'Delete check'}</button> : undefined} />
    <section className={`assessment-hero verdict-band-${scan.verdict}`}>
      <div className="assessment-label"><span className="section-overline">ASSESSMENT</span><VerdictBadge verdict={scan.verdict} /></div>
      <div className="assessment-main"><div><span className="assessment-title">{scan.verdict === 'lower-risk' ? 'Fewer concerning signals found.' : scan.verdict === 'high-risk' ? 'Several serious warning signs.' : scan.verdict === 'suspicious' ? 'Some signals deserve attention.' : 'The available evidence is inconclusive.'}</span><p>This is an automated assessment, not a guarantee or a substitute for trusted verification.</p></div><div className="assessment-score"><b>{scan.riskScore}</b><span>risk score / 100</span></div></div>
      <RiskMeter score={scan.riskScore} />
    </section>
    {scan.redactedPreview && <section className="panel preview-panel"><div className="section-overline">REDACTED INPUT PREVIEW</div><p data-testid="text-scan-preview">{scan.redactedPreview}</p></section>}
    <div className="detail-grid">
      <section className="panel indicator-panel"><div className="panel-heading"><div><span className="section-overline">EVIDENCE</span><h2>Signals found</h2></div><span className="small-pill">{scan.indicators.length} indicators</span></div>
        {scan.indicators.length ? <div className="indicator-list">{scan.indicators.map((indicator, index) => <article className={`indicator indicator-${indicator.severity}`} key={`${indicator.code}-${index}`} data-testid={`card-indicator-${indicator.code}-${index}`}><span className="indicator-symbol">{indicator.severity === 'high' ? <ShieldAlert size={17} /> : indicator.severity === 'warning' ? <TriangleAlert size={17} /> : <Activity size={17} />}</span><div><div className="indicator-heading"><strong>{indicator.title}</strong><span>{indicator.severity}</span></div><p>{indicator.detail}</p></div></article>)}</div> : <EmptyInline title="No indicators returned" copy="No specific signals were included in this assessment." />}
      </section>
      <aside className="detail-side">
        <section className="panel recommendations-panel"><div className="panel-heading"><div><span className="section-overline">NEXT STEPS</span><h2>Recommendations</h2></div></div>
          {scan.recommendations.length ? <ul className="recommendation-list">{scan.recommendations.map((item, index) => <li key={index} data-testid={`text-recommendation-${index}`}><span><Check size={14} /></span>{item}</li>)}</ul> : <EmptyInline title="No recommendations" copy="No next steps were provided for this scan." />}
        </section>
        {scan.urls.length > 0 && <section className="panel url-assessments"><div className="panel-heading"><div><span className="section-overline">LINKS IN THIS INPUT</span><h2>URL assessments</h2></div></div>
          {scan.urls.map((item, index) => <div className="url-assessment" key={`${item.url}-${index}`} data-testid={`card-url-assessment-${index}`}><div className="url-line"><Globe2 size={15} /><span>{item.url}</span></div><div className="url-assessment-meta"><VerdictBadge verdict={item.verdict} /><span>Risk {item.riskScore}/100</span></div>{item.indicators.map((indicator, n) => <p className="url-indicator" key={`${indicator.code}-${n}`}>{indicator.title}: {indicator.detail}</p>)}</div>)}
        </section>}
      </aside>
    </div>
    <section className="panel limitation-panel"><div className="limitation-icon"><TriangleAlert size={18} /></div><div><span className="section-overline">LIMITATIONS</span><h2>What this assessment cannot tell you</h2>{scan.limitations.length ? <ul>{scan.limitations.map((item, index) => <li key={index} data-testid={`text-limitation-${index}`}>{item}</li>)}</ul> : <p>No additional limitations were returned with this scan. Automated assessments can still miss context or new threats.</p>}<small>Assessment method version: {scan.modelVersion || 'not provided'}</small></div></section>
    {current.data?.user && <section className="feedback-panel"><div><span className="section-overline">HELP IMPROVE THE RECORD</span><h2>Was this assessment useful?</h2><p>Share whether the assessment matched what you observed.</p></div>{feedbackSent ? <span className="feedback-thanks" data-testid="status-feedback-success"><Check size={16} /> Feedback recorded</span> : <div className="feedback-actions">
      {([['correct', 'Looks right'], ['false-positive', 'False alarm'], ['false-negative', 'Missed a threat'], ['other', 'Other']] as const).map(([value, label]) => <button key={value} className="button button-outline button-small" onClick={() => sendFeedback(value)} disabled={feedback.isPending} data-testid={`button-feedback-${value}`}>{label}</button>)}
    </div>}{feedback.isError && <p className="form-error" role="alert" data-testid="status-feedback-error">Feedback could not be recorded. Please try again.</p>}</section>}
  </div>;
}

function SettingsPage() {
  const current = useGetCurrentUser();
  return <div className="page-wrap settings-page">
    <PageHeading eyebrow="PRIVACY & METHOD" title="Know what happens here." description="A straightforward account of what ScamShield checks, what it stores, and what an assessment can—and cannot—say." />
    <section className="settings-intro"><div className="settings-seal"><ShieldCheck size={25} /></div><div><span className="section-overline">A PRACTICAL SECURITY COMPANION</span><h2>Useful signals. Honest limits.</h2><p>ScamShield is built to help you pause and inspect. It is not a promise that a link or message is safe.</p></div></section>
    <div className="settings-sections">
      <section className="settings-section"><span className="settings-num">01</span><div><h2>What we look for</h2><p>Submitted links and message text are assessed for indicators associated with suspicious or potentially harmful content. Results can include a verdict, risk score, supporting indicators, recommendations, and limitations.</p><p>Checks do not open a URL in your browser. A scan is based on the evidence available to the service at the time.</p></div><div className="settings-art"><Search size={22} /><span>INPUT → SIGNALS</span></div></section>
      <section className="settings-section"><span className="settings-num">02</span><div><h2>Privacy and saved checks</h2><p>When signed in, scans are associated with your account so they can appear in your history. You can remove a saved scan from its detail page. The app uses a same-origin, HttpOnly session cookie for sign-in.</p><p>Avoid submitting passwords, one-time codes, financial details, or other secrets. A redacted preview may be shown with the saved result.</p></div><div className="settings-art"><LockKeyhole size={22} /><span>ACCOUNT-BOUND</span></div></section>
      <section className="settings-section"><span className="settings-num">03</span><div><h2>Where certainty ends</h2><p>A lower-risk result means fewer concerning indicators were found—not that a message or site is safe. New threats, short links, missing context, and changing destinations can all affect a check.</p><p>When in doubt, contact the organization through a number or website you already know. Do not use contact details in a suspicious message.</p></div><div className="settings-art settings-art-warn"><TriangleAlert size={22} /><span>NO GUARANTEE</span></div></section>
      <section className="settings-section"><span className="settings-num">04</span><div><h2>Feedback and improvement</h2><p>Feedback on an individual result can help us understand whether an assessment matched your experience. It does not change the assessment into a certainty, and feedback is tied to the scan you select.</p></div><div className="settings-art"><MessageSquareText size={22} /><span>HUMAN CONTEXT</span></div></section>
    </div>
    <div className="settings-account"><div><span className="section-overline">YOUR SESSION</span><strong data-testid="text-settings-session">{current.data?.user ? `Signed in as ${current.data.user.email}` : 'Not signed in'}</strong></div>{current.data?.user ? <Link href="/dashboard" className="text-link" data-testid="link-settings-dashboard">Account overview <ArrowRight size={15} /></Link> : <Link href="/login" className="button button-outline button-small" data-testid="link-settings-login">Sign in</Link>}</div>
  </div>;
}

function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const register = useRegister();
  const login = useLogin();
  const client = useQueryClient();
  const [, setLocation] = useLocation();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const pending = register.isPending || login.isPending;
  const error = register.error || login.error;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const onSuccess = (result: { user: { id: string; name: string; email: string; createdAt: string } }) => {
      client.setQueryData(getGetCurrentUserQueryKey(), { user: result.user });
      setLocation('/dashboard');
    };
    if (mode === 'register') register.mutate({ data: { name: name.trim(), email: email.trim(), password } }, { onSuccess });
    else login.mutate({ data: { email: email.trim(), password } }, { onSuccess });
  };
  return <div className="auth-layout">
    <section className="auth-art">
      <Brand />
      <div className="auth-art-copy"><span className="section-overline">A MOMENT TO CHECK</span><h1>Confidence starts<br />with a <em>closer look.</em></h1><p>Keep a record of what you checked, and return to the evidence when you need it.</p></div>
      <div className="auth-art-bottom"><ShieldCheck size={16} /> A careful companion, not a guarantee.</div>
    </section>
    <section className="auth-form-area">
      <Link href="/" className="auth-back" data-testid="link-auth-home"><ArrowLeft size={15} /> Back to ScamShield</Link>
      <div className="auth-form-wrap">
        <span className="section-overline">{mode === 'login' ? 'WELCOME BACK' : 'START WITH A PAUSE'}</span>
        <h2>{mode === 'login' ? 'Sign in to your account.' : 'Create your account.'}</h2>
        <p className="auth-intro">{mode === 'login' ? 'Your saved checks are waiting when you are.' : 'Save and revisit the checks that matter.'}</p>
        <form onSubmit={submit} className="auth-form">
          {mode === 'register' && <label>Your name<input value={name} onChange={e => setName(e.target.value)} autoComplete="name" required maxLength={100} placeholder="Name" data-testid="input-register-name" /></label>}
          <label>Email address<input type="email" value={email} onChange={e => setEmail(e.target.value)} autoComplete="email" required maxLength={254} placeholder="you@example.com" data-testid={`input-${mode}-email`} /></label>
          <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required minLength={mode === 'login' ? 1 : 10} maxLength={128} placeholder={mode === 'register' ? 'At least 10 characters' : 'Your password'} data-testid={`input-${mode}-password`} /></label>
          {error && <div className="form-error" role="alert" data-testid={`status-${mode}-error`}><CircleAlert size={16} /> We could not {mode === 'login' ? 'sign you in' : 'create your account'}. Check your details and try again.</div>}
          <button type="submit" className="button button-green auth-submit" disabled={pending} data-testid={`button-${mode}-submit`}>{pending ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'} <ArrowRight size={15} /></button>
        </form>
        <div className="auth-switch">{mode === 'login' ? <>New to ScamShield? <Link href="/register" data-testid="link-login-register">Create an account</Link></> : <>Already have an account? <Link href="/login" data-testid="link-register-login">Sign in</Link></>}</div>
        <div className="auth-privacy"><LockKeyhole size={14} /> Sign-in sessions use a secure HttpOnly cookie.</div>
      </div>
    </section>
  </div>;
}

function NotFoundPage() {
  return <div className="not-found-page">
    <span className="section-overline">404 / NOT FOUND</span>
    <div className="not-found-mark"><ShieldAlert size={25} /></div>
    <h1>This trail ends here.</h1>
    <p>That page is not part of your ScamShield workspace. Head back to a place you recognize.</p>
    <div className="not-found-actions"><Link href="/dashboard" className="button button-green" data-testid="link-not-found-dashboard">Go to overview <ArrowRight size={15} /></Link><Link href="/" className="text-link" data-testid="link-not-found-home">Return home</Link></div>
  </div>;
}

function Router() {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}><Shell><Switch>
    <Route path="/" component={Landing} />
    <Route path="/dashboard" component={Dashboard} />
    <Route path="/scan" component={ScanPage} />
    <Route path="/history" component={HistoryPage} />
    <Route path="/scans/:id" component={ScanDetail} />
    <Route path="/settings" component={SettingsPage} />
    <Route path="/login" component={() => <AuthPage mode="login" />} />
    <Route path="/register" component={() => <AuthPage mode="register" />} />
    <Route component={NotFoundPage} />
  </Switch></Shell></ErrorBoundary>;
}

function App() {
  return <QueryClientProvider client={queryClient}><TooltipProvider><WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}><Router /></WouterRouter><Toaster /></TooltipProvider></QueryClientProvider>;
}

export default App;
