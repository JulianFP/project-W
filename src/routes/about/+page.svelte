<script>
import CenterPage from "$lib/components/centerPage.svelte";
import { A, Hr, P, Span } from "flowbite-svelte";
</script>

<CenterPage title="What is Project W?">
  <P>Project W is a self-hostable <Span class="decoration-blue-400 dark:decoration-blue-600" underline>platform</Span> on which users can create <Span class="decoration-orange-400 dark:decoration-orange-500" underline>transcripts</Span> of their audio files (<Span class="decoration-green-400 dark:decoration-green-600" underline>speech-to-text</Span>). It leverages <Span class="decoration-violet-400 dark:decoration-violet-600" underline>OpenAIs Whisper</Span> model for the actual transcription while providing an <Span class="decoration-fuchsia-400 dark:decoration-fuchsia-600" underline>easy-to-use</Span> interface on which users can create and manage their transcription jobs.</P>
  <Hr class="bg-gray-400 w-96 h-1 mx-auto my-4 rounded"/>
  <P>This project was build and is being maintained mainly by <Span highlight="blue">Julian Partanen</Span> at the <A href="https://www.ssc.uni-heidelberg.de" target="_blank" rel="noopener noreferrer"> Scientific Software Center (SSC)</A> at Heidelberg university. Credits also go to <Span highlight="blue">Markus Everling</Span> for helping to build the prototype version as part of the university practical 'Research Software Engineering', to <Span highlight="blue">Dominic Kempf</Span> who guided the project from beginning to end, and to all the folks from the <A href="https://www.urz.uni-heidelberg.de" target="_blank" rel="noopener noreferrer">University Computing Center (URZ)</A> who deployed and maintain our universities instance and provided helpful feedback.</P>
</CenterPage>
