<script lang="ts">
import CenterPage from "$lib/components/centerPage.svelte";
import { A, Span } from "flowbite-svelte";

import type { components } from "$lib/utils/schema";

type Data = {
	about: components["schemas"]["AboutResponse"];
};
interface Props {
	data: Data;
}
let { data }: Props = $props();
</script>

<CenterPage title="Imprint of this instance">
  {#if data.about.imprint}
    <div class="flowbite-anchors">
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
</CenterPage>
