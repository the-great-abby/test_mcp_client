<script lang="ts">
  import { login } from '$lib/api/auth';
  let username = '';
  let password = '';
  let error = '';

  async function handleLogin() {
    try {
      await login(username, password);
      window.location.href = '/'; // or use goto from $app/navigation
    } catch (e) {
      error = e.message;
    }
  }
</script>

<form on:submit|preventDefault={handleLogin}>
  <input bind:value={username} placeholder="Username" required />
  <input type="password" bind:value={password} placeholder="Password" required />
  <button type="submit">Login</button>
  {#if error}<p style="color:red">{error}</p>{/if}
</form> 