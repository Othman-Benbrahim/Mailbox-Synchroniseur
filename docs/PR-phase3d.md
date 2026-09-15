# Texte de la PR — phase 3, lot 3d

Titre : Phase 3 (lot 3d) : miroir, seule fonction de suppression

Premier et seul code de suppression du produit. Il ne supprime qu'à destination.

- `--nodelete1` passé dans **tous** les modes : la boîte source n'est jamais touchée.
- Miroir (`--delete2`) désactivé par défaut. Marquage `\Deleted` seulement : imapsync
  activerait `uidexpunge2`/`expunge2` de lui-même, c'est explicitement désactivé. Vidage
  définitif derrière une option séparée.
- Quatre garde-fous cumulés : case décochée à chaque démarrage et jamais écrite dans un
  profil ; simulation réussie du même plan miroir déjà armé ; aperçu du nombre exact de
  suppressions issu de cette simulation ; confirmation par saisie de `SUPPRIMER`.
- Miroir refusé avec un filtre actif (les messages exclus seraient supprimés à destination).
- Bilan, historique et rapport exporté consignent le caractère destructif et le décompte.
- Le déplacement (`--delete1`) n'est pas livré et sort du périmètre ; limites de débit
  abandonnées. Motifs dans ROADMAP.md. AGENTS.md mis à jour.

Validation locale Linux : 170 tests de socle. Deux essais IMAP réels de miroir exécutés
avec pymap substitué à GreenMail (`docs/validation-3d-pymap.xml`).
**Exiger 170 / 170 / 23 passed, aucun ignoré, avant de fusionner.** Relire en priorité
`test_the_source_is_never_deleted_in_any_mode` et `test_confirmation_must_be_typed_exactly`.
