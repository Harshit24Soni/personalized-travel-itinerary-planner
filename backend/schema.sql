create table if not exists public.itinerary_plans (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users (id) on delete cascade,
    trip_id text not null,
    trip jsonb not null,
    created_at timestamptz not null default now(),
    unique (user_id, trip_id)
);

alter table public.itinerary_plans enable row level security;

create policy "Users can read their own itineraries"
    on public.itinerary_plans for select to authenticated
    using (auth.uid() = user_id);

create policy "Users can create their own itineraries"
    on public.itinerary_plans for insert to authenticated
    with check (auth.uid() = user_id);

create policy "Users can update their own itineraries"
    on public.itinerary_plans for update to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "Users can delete their own itineraries"
    on public.itinerary_plans for delete to authenticated
    using (auth.uid() = user_id);
