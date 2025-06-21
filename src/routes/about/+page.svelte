<script lang="ts">
import { version } from "$app/environment";

import CenterPage from "$lib/components/centerPage.svelte";
import { A, Heading, Hr, P, Span } from "flowbite-svelte";

import type { components } from "$lib/utils/schema";

type Data = {
	about: components["schemas"]["AboutResponse"];
};
interface Props {
	data: Data;
}
let { data }: Props = $props();

let [frontend_version, frontend_git_hash] = version.split("|");
</script>

<CenterPage title="About">
  <div>
    <Heading tag="h4" class="mb-2">What is Project-W?</Heading>
    <P>Project W is a self-hostable <Span class="decoration-blue-400 dark:decoration-blue-600" underline>platform</Span> on which users can create <Span class="decoration-orange-400 dark:decoration-orange-500" underline>transcripts</Span> of their audio files (<Span class="decoration-green-400 dark:decoration-green-600" underline>speech-to-text</Span>). It leverages <Span class="decoration-violet-400 dark:decoration-violet-600" underline>OpenAIs Whisper</Span> model for the actual transcription while providing an <Span class="decoration-fuchsia-400 dark:decoration-fuchsia-600" underline>easy-to-use</Span> interface on which users can create and manage their transcription jobs.</P>
  </div>

  {#if data.about.imprint}
    <Hr class="bg-gray-400 w-96 h-1 mx-auto my-0 rounded"/>

    <div class="flowbite-anchors">
      <Heading tag="h4" class="mb-2">Imprint of this instance</Heading>
      <dl class="text-gray-900 dark:text-white flex flex-col gap-2">
        <div>
          <dt><strong>Name:</strong></dt>
          <dd><Span highlight="blue">{data.about.imprint.name}</Span></dd>
        </div>
        <div>
          <dt><strong>Email:</strong></dt>
          <dt><A href="mailto:{data.about.imprint.email}">{data.about.imprint.email}</A></dt>
        </div>

        {#if data.about.imprint.additional_imprint_html}
          {@html data.about.imprint.additional_imprint_html}
        {/if}
      </dl>
    </div>
  {/if}

  <Hr class="bg-gray-400 w-96 h-1 mx-auto my-0 rounded"/>

  <div>
    <Heading tag="h4" class="mb-2">Version and source code information</Heading>
    <P>The backend is running on version {data.about.version}. <A href={data.about.source_code} target="_blank" rel="noopener noreferrer">It's source code</A> is checked out at git hash {data.about.git_hash}.</P>
    <P>The frontend is running on version {frontend_version}. <A href="https://github.com/JulianFP/project-W-frontend" target="_blank" rel="noopener noreferrer">It's source code</A> is checked out at git hash {frontend_git_hash}.</P>
    <P>The version and source code information for each runner can be viewed under the job details after a submitted job was assigned to the runner.</P>
  </div>

  <Hr class="bg-gray-400 w-96 h-1 mx-auto my-0 rounded"/>

  <div>
    <Heading tag="h4" class="mb-2">Credits</Heading>
    <P>This project was build and is being maintained mainly by <Span highlight="blue">Julian Partanen</Span> at the <A href="https://www.ssc.uni-heidelberg.de" target="_blank" rel="noopener noreferrer"> Scientific Software Center (SSC)</A> at Heidelberg university. Credits also go to <Span highlight="blue">Markus Everling</Span> for helping to build the prototype version as part of the university practical 'Research Software Engineering', to <Span highlight="blue">Dominic Kempf</Span> who mentored the practical and project and has been a great guidance along the way, and to all the folks from the <A href="https://www.urz.uni-heidelberg.de" target="_blank" rel="noopener noreferrer">University Computing Center (URZ)</A> who deployed and maintain our universities instance and provided helpful feedback.</P>
  </div>
</CenterPage>
