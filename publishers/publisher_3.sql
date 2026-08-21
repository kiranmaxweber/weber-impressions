-- Publisher 3. One confirmation email per order, in French. No status field, no dates
-- as columns — whatever is known is in the text. The adapter hands it to the model.
-- Row Level Security: anyone with the publishable key can read; nobody can write.

create table commandes (
  reference   text primary key,            -- Weber Impressions order number; all they track
  recu_le     timestamptz not null,
  raw_email   text not null
);

alter table commandes enable row level security;
create policy "public read" on commandes for select to anon using (true);

insert into commandes values (
  '94105',
  '2026-08-17 16:42:00+02',
$email$Objet : Votre commande 94105 — Modern Color

Bonjour,

Merci pour votre commande passée le 17 août par Weber Impressions.

1 × Fred Herzog, Modern Color — 85,00 USD

L'ouvrage est en préparation à l'atelier. Nous sommes une petite structure
et nous expédions nous-mêmes ; comptez sur une livraison aux États-Unis
autour du mardi 8 septembre. Nous vous écrirons le jour du départ avec le
numéro de suivi.

Rien n'est débité avant l'expédition. Si vous souhaitez annuler d'ici là,
répondez simplement à ce message.

Bien à vous,
Claire$email$
);
