<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import { Modal, Select, Label, Dropzone, Heading } from "flowbite-svelte";

  import WaitingSubmitButton from "./waitingSubmitButton.svelte";
  import { alerts } from "../utils/stores";
  import { postLoggedIn } from "../utils/httpRequests";

  const dispatchEvent = createEventDispatcher();

  function dropHandle(event: DragEvent): void {
    files = [];
    event.preventDefault();
    if (event.dataTransfer && event.dataTransfer.files) {
      [...event.dataTransfer.files].forEach((file: File, i: number) => {
        files.push(file);
        files = files; //to trigger reactivity
      });
    }
  };

  function handleChange(event: Event): void {
    files = [];
    const target = event.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      [...target.files].forEach((file: File, i: number) => {
        files.push(file);
        files = files; //to trigger reactivity
      });
    }
  };

  function showFileNames(files: File[]): string {
    if (files.length === 1) return files[0].name;
    let concat: string = files.length + " files: ";
    for(let file of files){
      concat += file.name + ", ";
    }

    if (concat.length > 50) {
      concat = concat.slice(0, 50);
      concat += '...';
    };
    if (concat[concat.length - 2] == ',') concat = concat.slice(0, concat.length-2);
    return concat;
  };

  async function submitAction(event: Event): Promise<void> {
    waitingForPromise = true;
    event.preventDefault();

    //send all requests at ones and wait for promises in parallel with "allSettled" method
    //show results to user ones all promises have settled
    let promises: Promise<{[key: string]: any}>[] = [];
    for(let file of files){
      if(language != "Automatic language detection"){
        promises.push(postLoggedIn("jobs/submit", {"file": file, "model": model, "language": language}));
      }
      else{ //null for automatic language detection
        promises.push(postLoggedIn("jobs/submit", {"file": file, "model": model}));
      }
    }
    let responses: {[key: string]: any} = await Promise.allSettled(promises);

    const successfulJobIds: number[] = [];
    for(let i: number = 0; i < files.length; i++){
      const response: {[key: string]: any} = responses[i].value;

      if(!response.ok){
        alerts.add("Error occurred while submitting job with filename '" + files[i].name + "': " + response.msg, "red")
      }
      else{
        alerts.add("You successfully submitted job with ID " + response.jobId.toString() + " and filename '" + files[i].name + "'", "green");
        successfulJobIds.push(response.jobId);
      }
    }

    open = false;
    waitingForPromise = false;

    if(successfulJobIds.length > 0) dispatchEvent('afterSubmit', {jobIds: successfulJobIds});
  }

  let models: {value: string, name: string}[] = [
    { value: "tiny", name: "Tiny"},
    { value: "tiny.en", name: "Tiny - English only"},
    { value: "base", name: "Base"},
    { value: "base.en", name: "Base - English only"},
    { value: "small", name: "Small"},
    { value: "small.en", name: "Small - English only"},
    { value: "medium", name: "Medium"},
    { value: "medium.en", name: "Medium - English only"},
    { value: "large", name: "Large"}
  ]
  let languages: string[] = [ "Automatic language detection", "Afrikaans","Albanian","Amharic","Arabic","Armenian","Assamese","Azerbaijani","Bashkir","Basque","Belarusian","Bengali","Bosnian","Breton","Bulgarian","Burmese","Cantonese","Castilian","Catalan","Chinese","Croatian","Czech","Danish","Dutch","English","Estonian","Faroese","Finnish","Flemish","French","Galician","Georgian","German","Greek","Gujarati","Haitian","Haitian Creole","Hausa","Hawaiian","Hebrew","Hindi","Hungarian","Icelandic","Indonesian","Italian","Japanese","Javanese","Kannada","Kazakh","Khmer","Korean","Lao","Latin","Latvian","Letzeburgesch","Lingala","Lithuanian","Luxembourgish","Macedonian","Malagasy","Malay","Malayalam","Maltese","Mandarin","Maori","Marathi","Moldavian","Moldovan","Mongolian","Myanmar","Nepali","Norwegian","Nynorsk","Occitan","Panjabi","Pashto","Persian","Polish","Portuguese","Punjabi","Pushto","Romanian","Russian","Sanskrit","Serbian","Shona","Sindhi","Sinhala","Sinhalese","Slovak","Slovenian","Somali","Spanish","Sundanese","Swahili","Swedish","Tagalog","Tajik","Tamil","Tatar","Telugu","Thai","Tibetan","Turkish","Turkmen","Ukrainian","Urdu","Uzbek","Valencian","Vietnamese","Welsh","Yiddish","Yoruba" ]

  let files: File[] = [];
  let model: string = "medium";
  let language: string = "Automatic language detection";

  let waitingForPromise: boolean = false;

  export let open: boolean = false;
</script>

<Modal bind:open={open} autoclose={false} class="w-fit">
  <form class="flex flex-col space-y-6" on:submit={submitAction}>
    <Heading tag="h3">{files.length > 1 ? "Submit " + files.length + " new transcription jobs" : "Submit a new transcription job"}</Heading>

    <div>
      <Label class="mb-2" for="language">Select a language (note that some models only understand English)</Label>
      <Select id="language" bind:value={language}>
        {#each languages as value}
          <option value={value} disabled={model.indexOf("en") != -1 && value != "English"}>{value}</option>
        {/each}
      </Select>
    </div>

    <div>
      <Label class="mb-2" for="models">Select a model (larger models will return a better result but will take longer)</Label>
      <Select id="models" bind:value={model}>
        {#each models as {value, name}}
          <option value={value} disabled={value.indexOf("en") != -1 && language != "English"}>{name}</option>
        {/each}
      </Select>
    </div>

    <div>
      <Label class="mb-2" for="upload_files">Upload one or more audio files. A transcription job will be created for each of the uploaded files</Label>
      <Dropzone
        multiple
        id="upload_files"
        on:drop={dropHandle}
        on:dragover={(event) => {
          event.preventDefault();
        }}
        on:change={handleChange}>
        <svg aria-hidden="true" class="mb-3 w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
        {#if files.length === 0}
          <p class="mb-2 text-sm text-gray-500 dark:text-gray-400"><span class="font-semibold">Click to upload</span> or drag and drop</p>
          <p class="text-xs text-gray-500 dark:text-gray-400">Audio files (mp3, m4a, aac, ...)</p>
        {:else}
          <p>{showFileNames(files)}</p>
        {/if}
      </Dropzone>
    </div>
    <WaitingSubmitButton class="w-full1" waiting={waitingForPromise}>Submit</WaitingSubmitButton>
  </form>
</Modal>
