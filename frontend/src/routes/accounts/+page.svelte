<script lang="ts">
    let { data } = $props();
    let accountForm = $state(false)

    $inspect(accountForm);
</script>

<div>
    <h1 class="text-3xl">Accounts</h1>
    <div>
        <h2 class="text-2xl">List of Accounts Down Here</h2>
        <!--I fetch somehow a list of all the accounts and display them here-->
        <ul>
            {#each data.accounts as account (account.id)}
                <li>{account.name} {account.current_balance}</li>
            {/each}
        </ul>
    </div>
    <div>
        <button onclick={() => accountForm = !accountForm}>New Account</button>
        {#if accountForm}
            <div>New Account Form</div>
            <form>
                
            </form>
        {/if}
    </div>
</div>