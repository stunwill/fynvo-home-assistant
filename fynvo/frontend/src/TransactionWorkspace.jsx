import TransactionWorkspaceCore from './TransactionWorkspaceCore.jsx';

const defaultMoney = (value) => {
  if (value === null || value === undefined || value === '') return '—';
  const number = Number(value);
  return Number.isFinite(number)
    ? new Intl.NumberFormat('en-AU', {
        style: 'currency',
        currency: 'AUD',
      }).format(number)
    : '—';
};

const defaultDateLabel = (value) => {
  if (!value) return 'Date unavailable';
  const raw = String(value).slice(0, 10);
  const [year, month, day] = raw.split('-').map(Number);
  const date = new Date(year, month - 1, day);
  return Number.isNaN(date.getTime())
    ? 'Date unavailable'
    : new Intl.DateTimeFormat('en-AU', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      }).format(date);
};

export default function TransactionWorkspace({
  money = defaultMoney,
  dateLabel = defaultDateLabel,
  ...props
}) {
  return (
    <TransactionWorkspaceCore
      {...props}
      money={money}
      dateLabel={dateLabel}
    />
  );
}
