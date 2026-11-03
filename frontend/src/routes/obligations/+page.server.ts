import type { PageServerLoad } from './$types';
import { getApiBaseUrl } from '#lib/server/api.ts';

export interface ObligationItem {
	id: number;
	name: string;
	due_day: number;
	amount: number;
	note: string | null;
	account_id: number | null;
	account_name: string | null;
	account_type: string | null;
	is_active: boolean;
	last_paid_date: string | null;
	last_paid_amount: number | null;
	created_at: string;
	next_due_date: string;
	days_until_due: number;
	is_overdue: boolean;
	is_paid_this_month: boolean;
}

export interface AccountOption {
	id: number;
	name: string;
	account_type: string;
	due_date: number | null;
	monthly_payment: number | null;
	current_balance?: number;
}

export const load: PageServerLoad = async ({ fetch }) => {
	const apiBase = getApiBaseUrl();

	const [oblsRes, accsRes, settingsRes] = await Promise.all([
		fetch(`${apiBase}/obligations/`),
		fetch(`${apiBase}/accounts/?is_active=true`),
		fetch(`${apiBase}/notifications/settings`)
	]);

	const obligations: ObligationItem[] = oblsRes.ok ? await oblsRes.json() : [];
	const allAccounts: AccountOption[] = accsRes.ok ? await accsRes.json() : [];
	const notificationSettings = settingsRes.ok ? await settingsRes.json() : null;

	// Filter accounts suitable for linking (credit cards, loans, or any account)
	const debtAccounts = allAccounts.filter(
		(a) => a.account_type === 'credit_card' || a.account_type === 'loan'
	);

	return {
		obligations,
		debtAccounts,
		allAccounts,
		notificationSettings
	};
};
