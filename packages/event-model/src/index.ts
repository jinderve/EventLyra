export type EventChannel = {
  id: string;
  title: string;
  room: string | null;
  language: string | null;
};

export type EventEdition = {
  id: string;
  title: string;
  sessions_per_gpu: number;
  channels: EventChannel[];
};
