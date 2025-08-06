export function timeAgo(date: Date): [string, number | null] {
	const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);

	let interval = Math.floor(seconds / 31536000);
	if (interval > 1) {
		return [`${interval.toString()} years ago`, null];
	}

	interval = Math.floor(seconds / 2592000);
	if (interval > 1) {
		return [`${interval.toString()} months ago`, null];
	}

	interval = Math.floor(seconds / 86400);
	if (interval > 1) {
		return [`${interval.toString()} days ago`, null];
	}

	interval = Math.floor(seconds / 3600);
	if (interval > 1) {
		return [
			`${interval.toString()} hours ago`,
			(3600 * (interval + 1) - seconds) * 1000,
		];
	}

	interval = Math.floor(seconds / 60);
	if (interval > 1) {
		return [
			`${interval.toString()} minutes ago`,
			(60 * (interval + 1) - seconds) * 1000,
		];
	}

	if (seconds < 10) return ["just now", (10 - seconds) * 1000];

	return [
		`${Math.floor(seconds)} seconds ago`,
		(10 * (Math.floor(seconds / 10) + 1) - seconds) * 1000,
	];
}

export function autoupdate_date_since(
	date_getter: () => Date,
	date_since_setter: (date_since: string) => void,
	first_time_date: Date | null = null,
): string {
	let date: Date;
	if (first_time_date != null) {
		date = first_time_date;
	} else {
		date = date_getter();
	}
	const [date_since, date_next_update] = timeAgo(date);
	date_since_setter(date_since);
	if (date_next_update) {
		setTimeout(() => {
			autoupdate_date_since(date_getter, date_since_setter);
		}, date_next_update);
	}
	return date_since;
}
