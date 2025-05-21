<script lang="ts">
import { Button } from "flowbite-svelte";
import type { ButtonProps } from "flowbite-svelte";

const props: ButtonProps = $props();
const { class: string, ...rest } = props;
const classes =
	props.color === "alternative"
		? `${props.class} border-gray-400 bg-slate-100 hover:bg-slate-50 cursor-pointer`
		: `${props.class} cursor-pointer`;
</script>
<Button class={classes} {...rest}/>
