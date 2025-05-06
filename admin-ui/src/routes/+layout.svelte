<script lang="ts">
	import '../app.css';
	import { user } from '$lib/stores/auth';
	
	let { children } = $props();
	$: isAdmin = $user?.is_admin;
</script>

{#if isAdmin}
	<slot />
{:else}
	<p>You must be an admin to access this page. <a href="/login">Login</a></p>
{/if}
