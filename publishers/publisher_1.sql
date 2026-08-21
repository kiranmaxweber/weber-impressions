-- Publisher 1. Clean JSON, English status vocabulary, ISO dates.
-- Row Level Security: anyone with the publishable key can read; nobody can write.

create table orders (
  order_ref          text primary key,
  marketplace_ref    text not null,        -- Weber Impressions order number
  title              text not null,
  author             text not null,
  status             text not null,        -- pending | shipped | delivered | cancelled
  dispatched_on      date,
  estimated_delivery date,
  carrier            text,
  tracking_number    text,
  ship_to_country    text not null
);

alter table orders enable row level security;
create policy "public read" on orders for select to anon using (true);

insert into orders values (
  'P1-30417', '94105', 'William Eggleston''s Guide', 'William Eggleston', 'shipped',
  '2026-08-17', '2026-08-25', 'DHL Express', '5820 4471 9903', 'US'
);
