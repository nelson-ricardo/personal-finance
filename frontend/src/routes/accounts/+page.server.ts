import { error } from '@sveltejs/kit';

import type { PageServerLoad } from './$types';

export interface Account {
    id: number;
    name: string;
    accountType: string;
    totalStatementBalance: number;
    interestSavingBalance: number;
    monthlyPayment: number;
    dueDate: number;
    isActive: boolean;
    currentBalance: number;
}

export const load: PageServerLoad = async({ fetch }) => {
    const res = await fetch("http://127.0.0.1:8000/accounts/?is_active=true")

    if(!res.ok) {
        throw error(res.status, 'Could not fetch accounts from backend');
    }

    const accounts = await res.json();

    return {
        accounts
    };
}