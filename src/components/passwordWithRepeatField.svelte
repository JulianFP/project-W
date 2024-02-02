<script lang="ts">
  import PasswordField from "./passwordField.svelte";

  let passwordVisible: boolean = false;
  let repeatedPassword: string;

  $: if(password !== repeatedPassword){
    error = true;
    //don't overwrite existing error messages if something else already threw an error
    if(!otherError) errorMessage = "'Password' and 'Repeat Password' contents don't match. Please check for typos"
  }

  export let password: string;
  export let error: boolean = false;
  export let otherError: boolean;
  export let errorMessage: string;
</script>

<PasswordField bind:value={password} bind:error={error} bind:passwordVisible={passwordVisible}>Password</PasswordField>
<PasswordField bind:value={repeatedPassword} bind:error={error} bind:passwordVisible={passwordVisible}>Repeat Password</PasswordField>
