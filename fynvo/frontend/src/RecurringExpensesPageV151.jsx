import RecurringExpensesPage from './RecurringExpensesPage.jsx';
import './recurring-v18.css';

export {
  DEFAULT_FILTERS,
  RANGE_OPTIONS,
  PAYMENT_METHOD_LABELS,
  PAYMENT_STATUS_LABELS,
  activeFilterCount,
  enrichScheduledPayments,
  filterScheduledPayments,
  sortScheduledPayments,
  summarisePayments,
} from './RecurringExpensesPage.jsx';

export default function RecurringExpensesPageV151(props) {
  return <RecurringExpensesPage {...props} onRefresh={props.onRefresh || (() => window.location.reload())}/>;
}
