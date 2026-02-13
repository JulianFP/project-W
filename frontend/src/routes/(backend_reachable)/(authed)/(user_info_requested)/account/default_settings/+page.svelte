<script lang="ts">
	import { Helper } from "flowbite-svelte";

	import CenterPage from "$lib/components/centerPage.svelte";
	import JobSettingsForm from "$lib/components/jobSettingsForm.svelte";
	import WaitingSubmitButton from "$lib/components/waitingSubmitButton.svelte";
	import { jobsSubmitSettings } from "$lib/generated";
	import { get_error_msg } from "$lib/utils/http_utils";

	let get_job_settings = $state(() => {
		return {};
	});
	let requery_job_settings = $state(async () => {});

	let waiting: boolean = $state(false);
	let errorOccurred: boolean = $state(false);
	let errorMsg: string = $state("");

	async function submitAction(reset: boolean) {
		errorOccurred = false;
		errorMsg = "";
		waiting = true;

		const body = reset ? {} : get_job_settings();
		const { error } = await jobsSubmitSettings({
			body: body,
			query: { is_new_default: true },
		});
		if (error) {
			errorMsg = get_error_msg(error);
			errorOccurred = true;
		}

		await requery_job_settings();
		waiting = false;
	}
</script>

<CenterPage title="Account default job settings">
  <form onsubmit={async () => {await submitAction(false);}}>
    <JobSettingsForm bind:get_job_settings={get_job_settings} bind:re_query={requery_job_settings}/>
    {#if errorOccurred}
      <Helper class="mb-2" color="red">{errorMsg}</Helper>
    {/if}

    <div class="mt-8 flex gap-2">
      <WaitingSubmitButton class="w-full" waiting={waiting}>Set default to selected values</WaitingSubmitButton>
      <WaitingSubmitButton class="w-full" color="alternative" type="button" onclick={async () => {await submitAction(true);}} waiting={waiting}>Reset to application-wide defaults</WaitingSubmitButton>
    </div>
  </form>
</CenterPage>
