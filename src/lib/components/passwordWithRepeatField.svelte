<script lang="ts">
import PasswordField from "./passwordField.svelte";

interface Props {
	value: string;
	error?: boolean;
	errorMsg: string;
	tabindex?: number;
	password_change: boolean;
}

let {
	value = $bindable(),
	error = $bindable(false),
	errorMsg = $bindable(),
	tabindex = 1,
	password_change = false,
}: Props = $props();

let passwordVisible = $state(false);
let repeatedValue: string = $state("");

$effect(() => {
	if (value !== repeatedValue) {
		error = true;
		errorMsg =
			"'Password' and 'Repeat Password' contents don't match. Please check for typos";
	} else {
		error = false;
		errorMsg = "";
	}
});

$effect(() => {
	if (value === "") repeatedValue = "";
});
</script>

<PasswordField password_new={true} bind:value={value} bind:error={error} bind:passwordVisible={passwordVisible} id={password_change ? "new_password" : "password"} autocomplete="new-password" helper_text="The password needs to have at least one lowercase letter, uppercase letter, number, special character and at least 12 characters in total" tabindex={tabindex}>{password_change ? "New password" : "Password"}</PasswordField>
<PasswordField password_new={true} bind:value={repeatedValue} bind:error={error} bind:passwordVisible={passwordVisible} id="password-repeat" autocomplete="new-password" tabindex={(+tabindex + 1).toString()}>{password_change ? "Repeat new password" : "Repeat password"}</PasswordField>
