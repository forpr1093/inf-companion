// Made-up sample data for ?demo=1 design review only. Titles are invented.
import { nowPlaying, personalBest, recentPlays } from "./stores";
import type { RecentPlay } from "./events";

export function demoPanels(): void {
  nowPlaying.set({ title: "Night Circuit", difficulty: "ANOTHER", level: 12, bpm: 174, notes: 1650 });
  personalBest.set({ score: 2817, notes: 1650, lamp: "HARD CLEAR", miss_count: 14, last_played: "2026-11-20", source: "official" });
  const plays: RecentPlay[] = [
    { title: "Night Circuit", difficulty: "ANOTHER", level: 12, score: 2743, notes: 1650, option: "RANDOM", played_at: "2026-11-23T21:40:00" },
    { title: "Glass Garden", difficulty: "LEGGENDARIA", level: 12, score: 1092, notes: 1560, option: "RANDOM", played_at: "2026-11-23T21:35:00" },
    { title: "Thousand Lanterns", difficulty: "HYPER", level: 10, score: 1812, notes: 1080, option: "S-RANDOM", played_at: "2026-11-23T21:31:00" },
    { title: "Cobalt Rain", difficulty: "ANOTHER", level: 11, score: 439, notes: 1163, option: "OFF", played_at: "2026-11-23T21:27:00" },
    { title: "Paper Comet", difficulty: "NORMAL", level: 7, score: 1301, notes: 720, option: null, played_at: "2026-11-23T21:22:00" },
    { title: "Sunday Engine", difficulty: "BEGINNER", level: 3, score: 590, notes: 340, option: "MIRROR", played_at: "2026-11-23T21:18:00" },
  ];
  recentPlays.set(plays);
}
