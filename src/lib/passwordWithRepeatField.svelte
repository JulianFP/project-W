<script lang="ts">
import { run } from "svelte/legacy";

import PasswordField from "./passwordField.svelte";

interface Props {
	value: string;
	error?: boolean;
	otherError: boolean;
	errorMessage: string;
	tabindex?: string;
}

let {
	value = $bindable(),
	error = $bindable(false),
	otherError,
	errorMessage = $bindable(),
	tabindex = "1",
}: Props = $props();

let passwordVisible = $state(false);
let repeatedValue: string = $state();

run(() => {
	if (value !== repeatedValue) {
		error = true;
		//don't overwrite existing error messages if something else already threw an error
		if (!otherError)
			errorMessage =
				"'Password' and 'Repeat Password' contents don't match. Please check for typos";
	}
});
</script>

<PasswordField bind:value={value} bind:error={error} bind:passwordVisible={passwordVisible} id="password" autocomplete="new-password" tabindex={tabindex}>Password</PasswordField>
<PasswordField bind:value={repeatedValue} bind:error={error} bind:passwordVisible={passwordVisible} id="password-repeat" autocomplete="new-password" tabindex={(+tabindex + 1).toString()}>Repeat Password</PasswordField>
