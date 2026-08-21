-- Publisher 2. Their own field names, Spanish status values, dates as dd/mm/yyyy text.
-- Row Level Security: anyone with the publishable key can read; nobody can write.

create table pedidos (
  numero_pedido      text primary key,
  referencia_tienda  text not null,        -- Weber Impressions order number
  titulo             text not null,
  autor              text not null,
  estado             text not null,        -- pendiente | enviado | entregado | cancelado
  fecha_envio        text,                 -- '19/08/2026' — their export format, not a date type
  entrega_estimada   text,
  paqueteria         text,
  numero_guia        text,
  pais_destino       text not null
);

alter table pedidos enable row level security;
create policy "public read" on pedidos for select to anon using (true);

insert into pedidos values (
  'RM-2026-08817', '94105', 'Cape Light', 'Joel Meyerowitz', 'enviado',
  '19/08/2026', '28/08/2026', 'Estafeta', '7731029548', 'Estados Unidos'
);
