<script>
  import { P, Span, Hr } from "flowbite-svelte";
  import CenterPage from "../components/centerPage.svelte";
</script>

<CenterPage title="What is Project W?">
  <P>Project W is a self-hostable <Span class="decoration-blue-400 dark:decoration-blue-600" underline>platform</Span> on which users can create <Span class="decoration-orange-400 dark:decoration-orange-500" underline>transcripts</Span> of their audio files (<Span class="decoration-green-400 dark:decoration-green-600" underline>speech-to-text</Span>). It leverages <Span class="decoration-violet-400 dark:decoration-violet-600" underline>OpenAIs Whisper</Span> model for the actual transcription while providing an <Span class="decoration-fuchsia-400 dark:decoration-fuchsia-600" underline>easy-to-use</Span> interface on which users can create and manage their transcription jobs.</P>
  <Hr classHr="bg-gray-400 w-96 h-1 mx-auto my-4 rounded"/>
  <P>This project was created by <Span highlight>Markus Everling</Span> and <Span highlight>Julian Partanen</Span> as part of the software practical "Research Software Engineering" at the university of Heidelberg during the winter term 2023/24.</P>
</CenterPage>
