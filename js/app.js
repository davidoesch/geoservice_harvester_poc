/*
 * GeoHarvester web application
 *
 * Loads data/catalog.json (built by build_catalog.py) and offers:
 *  - multilingual full-text search over all harvested datasets
 *  - filters by provider type, region and service type
 *  - a coverage map (which cantons / cities have matching data, which not)
 *  - "Meine Karte": combine datasets from any provider on one map and open
 *    them together in map.geo.admin.ch, QGIS (.qlr) or ArcGIS Pro (.lyrx)
 *
 * No build step, no framework. Libraries: OpenLayers + proj4 (global).
 */
(function () {
  "use strict";

  // ------------------------------------------------------------------ config
  const CATALOG_URL = "data/catalog.json";
  const BOUNDARIES_URL = "data/boundaries.json";
  const PAGE_SIZE = 40;
  // Upper limit of layers on the map at once: every layer is one image
  // request per pan/zoom to the provider's server.
  const MAX_SELECTION = 200;
  const MANY_LAYERS = 50;
  const CANTONS = ["ZH", "BE", "LU", "UR", "SZ", "OW", "NW", "GL", "ZG", "FR",
    "SO", "BS", "BL", "SH", "AR", "AI", "SG", "GR", "AG", "TG", "TI", "VD", "VS",
    "NE", "GE", "JU"];
  // map.geo.admin.ch zoom levels (LV95 resolutions in m/px for z = 0..13)
  const MAPGEO_RES = [650, 500, 250, 100, 50, 20, 10, 5, 2.5, 2, 1, 0.5, 0.25, 0.1];
  const SWISSTOPO_RES = [4000, 3750, 3500, 3250, 3000, 2750, 2500, 2250, 2000,
    1750, 1500, 1250, 1000, 750, 650, 500, 250, 100, 50, 20, 10, 5, 2.5, 2, 1.5,
    1, 0.5, 0.25, 0.1];
  const CH_EXTENT = [2485000, 1075000, 2834000, 1296000];
  // Sequential ramp (light steps 150 / 300 / 450 / 600) for coverage counts
  const RAMP = ["#b7d3f6", "#6da7ec", "#2a78d6", "#184f95"];
  const BINS = [1, 2, 4, 10]; // lower bounds: 1 | 2-3 | 4-9 | 10+

  // -------------------------------------------------------------------- i18n
  const I18N = {
    de: {
      skip: "Zur Suche springen", navAbout: "Über", navQuality: "Qualität", navData: "Daten",
      heroTitle: "Alle Geodienste der Schweiz. Eine Suche.",
      heroLede: "Bund, 26 Kantone, Städte und Liechtenstein – durchsuchen, kombinieren und sehen, wo Daten fehlen.",
      searchLabel: "Suche", searchPlaceholder: "Thema suchen, z. B. Bienen, Lärm, Wald …",
      topics: ["Bienen", "Lärm", "Wald", "Velo", "Solar", "Naturgefahren", "Bäume", "Grundwasser", "Denkmal", "Parkplätze"],
      kind_federal: "Bund", kind_canton: "Kantone", kind_city: "Städte", kind_intercantonal: "geodienste.ch",
      allRegions: "Alle Regionen", region: "Region", tabList: "Liste", tabMap: "Karte",
      results: (n) => n === 1 ? "1 Datensatz" : `${fmt(n)} Datensätze`,
      browse: (n) => `${fmt(n)} Datensätze im Katalog`,
      covSummary: (c, m, f) => [`Daten aus ${c} von 26 Kantonen`, m ? `${m} ${m === 1 ? "Stadt" : "Städte"}` : "", f ? `${f} national/kantonsübergreifend` : ""].filter(Boolean).join(" · "),
      addAll: (n) => `Alle ${fmt(n)} zur Karte`, addAllCapped: (m, n) => `Alle zur Karte (erste ${fmt(m)} von ${fmt(n)})`,
      addedN: (n) => `${fmt(n)} Layer zur Karte hinzugefügt`,
      noteMany: "Bei sehr vielen Layern wird map.geo.admin.ch langsam – für grosse Auswahlen besser QGIS oder ArcGIS Pro verwenden.", exportCsv: "Treffer als CSV",
      addToMap: "+ Karte", onMap: "✓ Karte", addToMapLabel: "Zur Karte hinzufügen",
      openMapGeo: "In map.geo.admin.ch öffnen", mapgeo: "map.geo.admin.ch",
      more: "mehr", less: "weniger", moreMenu: "Links ▾",
      metadata: "Metadaten", legend: "Legende", copyUrl: (t) => `${t}-Adresse kopieren`,
      openCap: (t) => `${t}-GetCapabilities öffnen`,
      copied: "In die Zwischenablage kopiert",
      selection: "Meine Karte", clear: "Leeren", share: "Link teilen",
      linkCopied: "Link kopiert – die Auswahl ist darin enthalten.",
      selectionEmpty: "Füge Datensätze mit «+ Karte» hinzu. Sie erscheinen hier und auf der Karte – auch aus verschiedenen Kantonen und Städten gleichzeitig.",
      coverageResults: "Suchresultate", coverageSelection: "Meine Karte", coverageOff: "Aus",
      legendNoData: "keine Daten", legendCity: "Stadt mit Daten", legendCount: "Datensätze:",
      legendClick: "Klicke auf eine Region, um die Liste zu filtern.",
      legendSelection: "Abdeckung deiner Auswahl. Schraffiert = keine Daten.",
      national: (n) => `+ ${fmt(n)} nationale Datensätze (ganze Schweiz)`,
      basemap: "Hintergrund", bg_grau: "Landeskarte grau", bg_farbe: "Landeskarte farbig", bg_luftbild: "Luftbild", bg_none: "Kein Hintergrund",
      showMore: (n) => `Weitere ${fmt(n)} anzeigen`,
      noResults: "Keine Treffer", noResultsHint: "Versuche einen allgemeineren Begriff, eine andere Sprache oder entferne Filter.",
      startTitle: "Wonach suchst du?",
      startHint: "Tippe ein Thema – die Suche kennt Synonyme auf Deutsch, Französisch, Italienisch und Englisch.",
      loading: "Katalog wird geladen …", loadError: "Der Katalog konnte nicht geladen werden.",
      zoomTo: "Auf Layer zoomen", remove: "Entfernen", opacity: "Deckkraft", toggleLegend: "Legende ein/aus",
      st_loading: "lädt …", st_ok: "angezeigt", st_err: "Dienst liefert kein Bild", st_cors: "keine Vorschau im Browser – in QGIS/ArcGIS öffnen", st_wfs: "Vektordaten (WFS)",
      noteWfs: (n) => `${n} WFS-Layer ${n === 1 ? "kann" : "können"} in map.geo.admin.ch nicht angezeigt werden – nutze dafür QGIS oder ArcGIS Pro.`,
      tooMany: (n) => `Maximal ${n} Layer gleichzeitig.`,
      tipOwn: (n) => `${n} kantonale Datensätze`, tipInter: (n) => `${n} kantonsübergreifend (geodienste.ch)`,
      tipCity: (n) => `${n} Datensätze der Stadt`, tipNone: "keine Datensätze", tipClick: "Klicken zum Filtern",
      aboutTitle: "Über GeoHarvester",
      about: [
        "GeoHarvester erntet jede Woche automatisch die Metadaten aller offenen <strong>WMS-, WMTS- und WFS-Dienste</strong> des Bundes, der Kantone, von Städten und des Fürstentums Liechtenstein. Die Liste der Dienste wird aus <a href=\"https://opendata.swiss\">opendata.swiss</a>, <a href=\"https://www.geocat.ch\">geocat.ch</a>, <a href=\"https://www.geodienste.ch\">geodienste.ch</a> und den Geoportalen der Kantone und Städte zusammengetragen und geprüft.",
        "So werden auch Datensätze auffindbar, die in keinem Katalog erfasst sind. Suche ein Thema, lege Datensätze verschiedener Anbieter auf <strong>eine Karte</strong>, erkenne Lücken in der Abdeckung und öffne alles gemeinsam in map.geo.admin.ch, QGIS oder ArcGIS Pro.",
        "Ein Proof of Concept, entstanden aus der <a href=\"https://github.com/GeoUnconference/discussions/discussions/38\">4. GeoUnconference</a>. Hintergrund im <a href=\"https://www.linkedin.com/pulse/geoharvesting-unexploiting-seo-treasures-geoservices-david-oesch/\">Blogpost</a>."
      ],
      kpiDatasets: "Datensätze", kpiEndpoints: "Dienst-Endpunkte", kpiOwners: "Anbieter", kpiUpdated: "Stand",
      qualityTitle: "Qualität der Metadaten",
      qualityIntro: "Wie vollständig beschreiben die Anbieter ihre Layer? Anteil der Layer mit Beschreibung, Stichwörtern, Link zu Metadaten und Kontaktangabe. Klicke auf eine Spalte zum Sortieren.",
      colOwner: "Anbieter", colEndpoints: "Endpunkte", colLayers: "Layer", colAbstract: "Beschreibung", colKeywords: "Stichwörter", colMetadata: "Metadaten", colContact: "Kontakt",
      dataTitle: "Daten & Mitmachen",
      data: [
        "Alle Daten sind frei verfügbar und werden wöchentlich aktualisiert:",
        "<ul><li><a href=\"data/geoservices_CH.csv\">geoservices_CH.csv</a> – ein Eintrag pro Dienst und Layer (<a href=\"data/geoservices_CH.parquet\">Parquet</a>)</li><li><a href=\"data/geodata_CH.csv\">geodata_CH.csv</a> – ein Eintrag pro Datensatz mit Links zu WMS, WMTS und WFS (<a href=\"data/geodata_CH.parquet\">Parquet</a>)</li><li><a href=\"data/geoservices_stats_CH.csv\">geoservices_stats_CH.csv</a> – Qualitätsstatistik pro Anbieter</li><li><a href=\"https://github.com/davidoesch/geoservice_harvester_poc/blob/main/sources.csv\">sources.csv</a> – alle geprüften Dienst-Endpunkte</li></ul>",
        "Fehlt ein Dienst oder ist einer fehlerhaft? Ergänze <code>sources.csv</code> per Pull Request oder eröffne ein <a href=\"https://github.com/davidoesch/geoservice_harvester_poc/issues\">Issue</a>. Dienste mit Problemen beim letzten Lauf: <a href=\"https://github.com/davidoesch/geoservice_harvester_poc/blob/main/ISSUES.md\">ISSUES.md</a>."
      ],
      footerIssues: "Dienste mit Problemen", footerBase: "Hintergrundkarte © swisstopo",
      updated: (d) => `Stand: ${d}`, theme: "Farbschema wechseln", qgisDone: "QGIS-Layerdatei heruntergeladen – per Drag & Drop in QGIS ziehen.", arcgisDone: "ArcGIS-Pro-Layerdatei heruntergeladen – per Drag & Drop in die Karte ziehen.",
      mapLabel: "Karte der Schweiz"
    },
    fr: {
      skip: "Aller à la recherche", navAbout: "À propos", navQuality: "Qualité", navData: "Données",
      heroTitle: "Tous les géoservices de Suisse. Une seule recherche.",
      heroLede: "Confédération, 26 cantons, villes et Liechtenstein – rechercher, combiner et voir où les données manquent.",
      searchLabel: "Recherche", searchPlaceholder: "Chercher un thème, p. ex. abeilles, bruit, forêt …",
      topics: ["Abeilles", "Bruit", "Forêt", "Vélo", "Solaire", "Dangers naturels", "Arbres", "Eaux souterraines", "Patrimoine", "Parking"],
      kind_federal: "Confédération", kind_canton: "Cantons", kind_city: "Villes", kind_intercantonal: "geodienste.ch",
      allRegions: "Toutes les régions", region: "Région", tabList: "Liste", tabMap: "Carte",
      results: (n) => n === 1 ? "1 jeu de données" : `${fmt(n)} jeux de données`,
      browse: (n) => `${fmt(n)} jeux de données dans le catalogue`,
      covSummary: (c, m, f) => [`Données de ${c} cantons sur 26`, m ? `${m} ${m === 1 ? "ville" : "villes"}` : "", f ? `${f} nationaux/intercantonaux` : ""].filter(Boolean).join(" · "),
      addAll: (n) => `Ajouter les ${fmt(n)} à la carte`, addAllCapped: (m, n) => `Tout ajouter à la carte (${fmt(m)} premiers sur ${fmt(n)})`,
      addedN: (n) => `${fmt(n)} couches ajoutées à la carte`,
      noteMany: "Avec beaucoup de couches, map.geo.admin.ch devient lent – pour de grandes sélections, préférez QGIS ou ArcGIS Pro.", exportCsv: "Résultats en CSV",
      addToMap: "+ Carte", onMap: "✓ Carte", addToMapLabel: "Ajouter à la carte",
      openMapGeo: "Ouvrir dans map.geo.admin.ch", mapgeo: "map.geo.admin.ch",
      more: "plus", less: "moins", moreMenu: "Liens ▾",
      metadata: "Métadonnées", legend: "Légende", copyUrl: (t) => `Copier l'adresse ${t}`,
      openCap: (t) => `Ouvrir GetCapabilities ${t}`,
      copied: "Copié dans le presse-papiers",
      selection: "Ma carte", clear: "Vider", share: "Partager le lien",
      linkCopied: "Lien copié – la sélection y est incluse.",
      selectionEmpty: "Ajoutez des jeux de données avec « + Carte ». Ils apparaissent ici et sur la carte – même de cantons et villes différents.",
      coverageResults: "Résultats", coverageSelection: "Ma carte", coverageOff: "Masquer",
      legendNoData: "pas de données", legendCity: "ville avec données", legendCount: "Jeux de données :",
      legendClick: "Cliquez sur une région pour filtrer la liste.",
      legendSelection: "Couverture de votre sélection. Hachuré = pas de données.",
      national: (n) => `+ ${fmt(n)} jeux de données nationaux (toute la Suisse)`,
      basemap: "Fond de carte", bg_grau: "Carte nationale grise", bg_farbe: "Carte nationale couleur", bg_luftbild: "Image aérienne", bg_none: "Aucun fond",
      showMore: (n) => `Afficher ${fmt(n)} de plus`,
      noResults: "Aucun résultat", noResultsHint: "Essayez un terme plus général, une autre langue ou retirez des filtres.",
      startTitle: "Que cherchez-vous ?",
      startHint: "Tapez un thème – la recherche connaît des synonymes en français, allemand, italien et anglais.",
      loading: "Chargement du catalogue …", loadError: "Le catalogue n'a pas pu être chargé.",
      zoomTo: "Zoomer sur la couche", remove: "Retirer", opacity: "Opacité", toggleLegend: "Afficher/masquer la légende",
      st_loading: "chargement …", st_ok: "affiché", st_err: "le service ne renvoie pas d'image", st_cors: "pas d'aperçu dans le navigateur – ouvrir dans QGIS/ArcGIS", st_wfs: "données vectorielles (WFS)",
      noteWfs: (n) => `${n} couche(s) WFS ne peuvent pas être affichées dans map.geo.admin.ch – utilisez QGIS ou ArcGIS Pro.`,
      tooMany: (n) => `${n} couches au maximum.`,
      tipOwn: (n) => `${n} jeux de données cantonaux`, tipInter: (n) => `${n} intercantonaux (geodienste.ch)`,
      tipCity: (n) => `${n} jeux de données de la ville`, tipNone: "aucun jeu de données", tipClick: "Cliquer pour filtrer",
      aboutTitle: "À propos de GeoHarvester",
      about: [
        "GeoHarvester moissonne chaque semaine les métadonnées de tous les services <strong>WMS, WMTS et WFS</strong> ouverts de la Confédération, des cantons, des villes et de la Principauté de Liechtenstein. La liste des services est compilée et vérifiée à partir d'<a href=\"https://opendata.swiss\">opendata.swiss</a>, de <a href=\"https://www.geocat.ch\">geocat.ch</a>, de <a href=\"https://www.geodienste.ch\">geodienste.ch</a> et des géoportails cantonaux et communaux.",
        "Ainsi, même les jeux de données absents des catalogues deviennent trouvables. Cherchez un thème, combinez des données de plusieurs fournisseurs sur <strong>une carte</strong>, repérez les lacunes et ouvrez le tout dans map.geo.admin.ch, QGIS ou ArcGIS Pro.",
        "Une preuve de concept issue de la <a href=\"https://github.com/GeoUnconference/discussions/discussions/38\">4e GeoUnconference</a>. Contexte dans l'<a href=\"https://www.linkedin.com/pulse/geoharvesting-unexploiting-seo-treasures-geoservices-david-oesch/\">article de blog</a>."
      ],
      kpiDatasets: "Jeux de données", kpiEndpoints: "Points d'accès", kpiOwners: "Fournisseurs", kpiUpdated: "État",
      qualityTitle: "Qualité des métadonnées",
      qualityIntro: "Les fournisseurs décrivent-ils bien leurs couches ? Part des couches avec description, mots-clés, lien vers les métadonnées et contact. Cliquez sur une colonne pour trier.",
      colOwner: "Fournisseur", colEndpoints: "Points d'accès", colLayers: "Couches", colAbstract: "Description", colKeywords: "Mots-clés", colMetadata: "Métadonnées", colContact: "Contact",
      dataTitle: "Données & contribuer",
      data: [
        "Toutes les données sont libres et mises à jour chaque semaine :",
        "<ul><li><a href=\"data/geoservices_CH.csv\">geoservices_CH.csv</a> – une entrée par service et couche (<a href=\"data/geoservices_CH.parquet\">Parquet</a>)</li><li><a href=\"data/geodata_CH.csv\">geodata_CH.csv</a> – une entrée par jeu de données avec liens WMS, WMTS et WFS (<a href=\"data/geodata_CH.parquet\">Parquet</a>)</li><li><a href=\"data/geoservices_stats_CH.csv\">geoservices_stats_CH.csv</a> – statistiques de qualité par fournisseur</li><li><a href=\"https://github.com/davidoesch/geoservice_harvester_poc/blob/main/sources.csv\">sources.csv</a> – tous les points d'accès vérifiés</li></ul>",
        "Un service manque ou est erroné ? Complétez <code>sources.csv</code> par pull request ou ouvrez une <a href=\"https://github.com/davidoesch/geoservice_harvester_poc/issues\">issue</a>. Services en erreur lors du dernier passage : <a href=\"https://github.com/davidoesch/geoservice_harvester_poc/blob/main/ISSUES.md\">ISSUES.md</a>."
      ],
      footerIssues: "Services en erreur", footerBase: "Fond de carte © swisstopo",
      updated: (d) => `État : ${d}`, theme: "Changer de thème", qgisDone: "Fichier de couches QGIS téléchargé – glissez-le dans QGIS.", arcgisDone: "Fichier de couches ArcGIS Pro téléchargé – glissez-le dans la carte.",
      mapLabel: "Carte de la Suisse"
    },
    it: {
      skip: "Vai alla ricerca", navAbout: "Info", navQuality: "Qualità", navData: "Dati",
      heroTitle: "Tutti i geoservizi della Svizzera. Una sola ricerca.",
      heroLede: "Confederazione, 26 cantoni, città e Liechtenstein – cercare, combinare e vedere dove mancano i dati.",
      searchLabel: "Ricerca", searchPlaceholder: "Cerca un tema, p. es. api, rumore, bosco …",
      topics: ["Apicoltura", "Rumore", "Bosco", "Bicicletta", "Solare", "Pericoli naturali", "Alberi", "Acque sotterranee", "Beni culturali", "Posteggi"],
      kind_federal: "Confederazione", kind_canton: "Cantoni", kind_city: "Città", kind_intercantonal: "geodienste.ch",
      allRegions: "Tutte le regioni", region: "Regione", tabList: "Elenco", tabMap: "Carta",
      results: (n) => n === 1 ? "1 set di dati" : `${fmt(n)} set di dati`,
      browse: (n) => `${fmt(n)} set di dati nel catalogo`,
      covSummary: (c, m, f) => [`Dati da ${c} cantoni su 26`, m ? `${m} ${m === 1 ? "città" : "città"}` : "", f ? `${f} nazionali/intercantonali` : ""].filter(Boolean).join(" · "),
      addAll: (n) => `Aggiungi tutti i ${fmt(n)} alla carta`, addAllCapped: (m, n) => `Aggiungi tutti alla carta (primi ${fmt(m)} di ${fmt(n)})`,
      addedN: (n) => `${fmt(n)} livelli aggiunti alla carta`,
      noteMany: "Con molti livelli map.geo.admin.ch diventa lento – per selezioni grandi meglio QGIS o ArcGIS Pro.", exportCsv: "Risultati in CSV",
      addToMap: "+ Carta", onMap: "✓ Carta", addToMapLabel: "Aggiungi alla carta",
      openMapGeo: "Apri in map.geo.admin.ch", mapgeo: "map.geo.admin.ch",
      more: "di più", less: "di meno", moreMenu: "Link ▾",
      metadata: "Metadati", legend: "Legenda", copyUrl: (t) => `Copia indirizzo ${t}`,
      openCap: (t) => `Apri GetCapabilities ${t}`,
      copied: "Copiato negli appunti",
      selection: "La mia carta", clear: "Svuota", share: "Condividi link",
      linkCopied: "Link copiato – contiene la selezione.",
      selectionEmpty: "Aggiungi set di dati con «+ Carta». Appaiono qui e sulla carta – anche da cantoni e città diversi.",
      coverageResults: "Risultati", coverageSelection: "La mia carta", coverageOff: "Nascondi",
      legendNoData: "nessun dato", legendCity: "città con dati", legendCount: "Set di dati:",
      legendClick: "Clicca su una regione per filtrare l'elenco.",
      legendSelection: "Copertura della tua selezione. Tratteggiato = nessun dato.",
      national: (n) => `+ ${fmt(n)} set di dati nazionali (tutta la Svizzera)`,
      basemap: "Sfondo", bg_grau: "Carta nazionale grigia", bg_farbe: "Carta nazionale a colori", bg_luftbild: "Immagine aerea", bg_none: "Nessuno sfondo",
      showMore: (n) => `Mostra altri ${fmt(n)}`,
      noResults: "Nessun risultato", noResultsHint: "Prova un termine più generale, un'altra lingua o rimuovi i filtri.",
      startTitle: "Cosa cerchi?",
      startHint: "Digita un tema – la ricerca conosce sinonimi in italiano, tedesco, francese e inglese.",
      loading: "Caricamento del catalogo …", loadError: "Impossibile caricare il catalogo.",
      zoomTo: "Zoom sul livello", remove: "Rimuovi", opacity: "Opacità", toggleLegend: "Mostra/nascondi legenda",
      st_loading: "caricamento …", st_ok: "visualizzato", st_err: "il servizio non restituisce immagini", st_cors: "nessuna anteprima nel browser – apri in QGIS/ArcGIS", st_wfs: "dati vettoriali (WFS)",
      noteWfs: (n) => `${n} livello/i WFS non possono essere visualizzati in map.geo.admin.ch – usa QGIS o ArcGIS Pro.`,
      tooMany: (n) => `Al massimo ${n} livelli.`,
      tipOwn: (n) => `${n} set di dati cantonali`, tipInter: (n) => `${n} intercantonali (geodienste.ch)`,
      tipCity: (n) => `${n} set di dati della città`, tipNone: "nessun set di dati", tipClick: "Clicca per filtrare",
      aboutTitle: "Informazioni su GeoHarvester",
      about: [
        "GeoHarvester raccoglie ogni settimana i metadati di tutti i servizi <strong>WMS, WMTS e WFS</strong> aperti della Confederazione, dei cantoni, delle città e del Principato del Liechtenstein. L'elenco dei servizi è compilato e verificato da <a href=\"https://opendata.swiss\">opendata.swiss</a>, <a href=\"https://www.geocat.ch\">geocat.ch</a>, <a href=\"https://www.geodienste.ch\">geodienste.ch</a> e dai geoportali cantonali e comunali.",
        "Così diventano reperibili anche set di dati non registrati in alcun catalogo. Cerca un tema, combina dati di più fornitori su <strong>una carta</strong>, individua le lacune e apri tutto in map.geo.admin.ch, QGIS o ArcGIS Pro.",
        "Un proof of concept nato dalla <a href=\"https://github.com/GeoUnconference/discussions/discussions/38\">4a GeoUnconference</a>. Contesto nel <a href=\"https://www.linkedin.com/pulse/geoharvesting-unexploiting-seo-treasures-geoservices-david-oesch/\">post del blog</a>."
      ],
      kpiDatasets: "Set di dati", kpiEndpoints: "Endpoint", kpiOwners: "Fornitori", kpiUpdated: "Stato",
      qualityTitle: "Qualità dei metadati",
      qualityIntro: "Quanto descrivono bene i fornitori i loro livelli? Quota di livelli con descrizione, parole chiave, link ai metadati e contatto. Clicca su una colonna per ordinare.",
      colOwner: "Fornitore", colEndpoints: "Endpoint", colLayers: "Livelli", colAbstract: "Descrizione", colKeywords: "Parole chiave", colMetadata: "Metadati", colContact: "Contatto",
      dataTitle: "Dati & partecipare",
      data: [
        "Tutti i dati sono liberi e aggiornati settimanalmente:",
        "<ul><li><a href=\"data/geoservices_CH.csv\">geoservices_CH.csv</a> – una voce per servizio e livello (<a href=\"data/geoservices_CH.parquet\">Parquet</a>)</li><li><a href=\"data/geodata_CH.csv\">geodata_CH.csv</a> – una voce per set di dati con link WMS, WMTS e WFS (<a href=\"data/geodata_CH.parquet\">Parquet</a>)</li><li><a href=\"data/geoservices_stats_CH.csv\">geoservices_stats_CH.csv</a> – statistiche di qualità per fornitore</li><li><a href=\"https://github.com/davidoesch/geoservice_harvester_poc/blob/main/sources.csv\">sources.csv</a> – tutti gli endpoint verificati</li></ul>",
        "Manca un servizio o è errato? Completa <code>sources.csv</code> con una pull request o apri una <a href=\"https://github.com/davidoesch/geoservice_harvester_poc/issues\">issue</a>. Servizi con problemi nell'ultima esecuzione: <a href=\"https://github.com/davidoesch/geoservice_harvester_poc/blob/main/ISSUES.md\">ISSUES.md</a>."
      ],
      footerIssues: "Servizi con problemi", footerBase: "Sfondo © swisstopo",
      updated: (d) => `Stato: ${d}`, theme: "Cambia tema", qgisDone: "File di livelli QGIS scaricato – trascinalo in QGIS.", arcgisDone: "File di livelli ArcGIS Pro scaricato – trascinalo nella carta.",
      mapLabel: "Carta della Svizzera"
    },
    en: {
      skip: "Skip to search", navAbout: "About", navQuality: "Quality", navData: "Data",
      heroTitle: "Every geoservice in Switzerland. One search.",
      heroLede: "Federal government, 26 cantons, cities and Liechtenstein – search, combine and see where data is missing.",
      searchLabel: "Search", searchPlaceholder: "Search a topic, e.g. bees, noise, forest …",
      topics: ["Bees", "Noise", "Forest", "Cycling", "Solar", "Natural hazards", "Trees", "Groundwater", "Heritage", "Parking"],
      kind_federal: "Federal", kind_canton: "Cantons", kind_city: "Cities", kind_intercantonal: "geodienste.ch",
      allRegions: "All regions", region: "Region", tabList: "List", tabMap: "Map",
      results: (n) => n === 1 ? "1 dataset" : `${fmt(n)} datasets`,
      browse: (n) => `${fmt(n)} datasets in the catalogue`,
      covSummary: (c, m, f) => [`Data from ${c} of 26 cantons`, m ? `${m} ${m === 1 ? "city" : "cities"}` : "", f ? `${f} national/intercantonal` : ""].filter(Boolean).join(" · "),
      addAll: (n) => `Add all ${fmt(n)} to map`, addAllCapped: (m, n) => `Add all to map (first ${fmt(m)} of ${fmt(n)})`,
      addedN: (n) => `${fmt(n)} layers added to the map`,
      noteMany: "With very many layers map.geo.admin.ch gets slow – for large selections QGIS or ArcGIS Pro work better.", exportCsv: "Results as CSV",
      addToMap: "+ Map", onMap: "✓ Map", addToMapLabel: "Add to map",
      openMapGeo: "Open in map.geo.admin.ch", mapgeo: "map.geo.admin.ch",
      more: "more", less: "less", moreMenu: "Links ▾",
      metadata: "Metadata", legend: "Legend", copyUrl: (t) => `Copy ${t} address`,
      openCap: (t) => `Open ${t} GetCapabilities`,
      copied: "Copied to clipboard",
      selection: "My map", clear: "Clear", share: "Share link",
      linkCopied: "Link copied – it contains your selection.",
      selectionEmpty: "Add datasets with “+ Map”. They show up here and on the map – even from different cantons and cities at once.",
      coverageResults: "Search results", coverageSelection: "My map", coverageOff: "Off",
      legendNoData: "no data", legendCity: "city with data", legendCount: "Datasets:",
      legendClick: "Click a region to filter the list.",
      legendSelection: "Coverage of your selection. Hatched = no data.",
      national: (n) => `+ ${fmt(n)} national datasets (all of Switzerland)`,
      basemap: "Basemap", bg_grau: "National map grey", bg_farbe: "National map colour", bg_luftbild: "Aerial imagery", bg_none: "No basemap",
      showMore: (n) => `Show ${fmt(n)} more`,
      noResults: "No results", noResultsHint: "Try a broader term, another language or remove filters.",
      startTitle: "What are you looking for?",
      startHint: "Type a topic – the search knows synonyms in German, French, Italian and English.",
      loading: "Loading catalogue …", loadError: "The catalogue could not be loaded.",
      zoomTo: "Zoom to layer", remove: "Remove", opacity: "Opacity", toggleLegend: "Toggle legend",
      st_loading: "loading …", st_ok: "shown", st_err: "service returns no image", st_cors: "no browser preview – open in QGIS/ArcGIS", st_wfs: "vector data (WFS)",
      noteWfs: (n) => `${n} WFS layer(s) cannot be shown in map.geo.admin.ch – use QGIS or ArcGIS Pro.`,
      tooMany: (n) => `At most ${n} layers at once.`,
      tipOwn: (n) => `${n} cantonal datasets`, tipInter: (n) => `${n} intercantonal (geodienste.ch)`,
      tipCity: (n) => `${n} city datasets`, tipNone: "no datasets", tipClick: "Click to filter",
      aboutTitle: "About GeoHarvester",
      about: [
        "Every week GeoHarvester automatically harvests the metadata of all open <strong>WMS, WMTS and WFS services</strong> of the Swiss federal government, the cantons, cities and the Principality of Liechtenstein. The list of services is compiled and validated from <a href=\"https://opendata.swiss\">opendata.swiss</a>, <a href=\"https://www.geocat.ch\">geocat.ch</a>, <a href=\"https://www.geodienste.ch\">geodienste.ch</a> and cantonal and municipal geoportals.",
        "This makes datasets findable that are missing from every catalogue. Search a topic, combine datasets from several providers on <strong>one map</strong>, spot gaps in coverage and open everything together in map.geo.admin.ch, QGIS or ArcGIS Pro.",
        "A proof of concept that started at the <a href=\"https://github.com/GeoUnconference/discussions/discussions/38\">4th GeoUnconference</a>. Background in the <a href=\"https://www.linkedin.com/pulse/geoharvesting-unexploiting-seo-treasures-geoservices-david-oesch/\">blog post</a>."
      ],
      kpiDatasets: "Datasets", kpiEndpoints: "Service endpoints", kpiOwners: "Providers", kpiUpdated: "Updated",
      qualityTitle: "Metadata quality",
      qualityIntro: "How well do providers describe their layers? Share of layers with an abstract, keywords, a metadata link and a contact. Click a column to sort.",
      colOwner: "Provider", colEndpoints: "Endpoints", colLayers: "Layers", colAbstract: "Abstract", colKeywords: "Keywords", colMetadata: "Metadata", colContact: "Contact",
      dataTitle: "Data & contributing",
      data: [
        "All data is open and updated weekly:",
        "<ul><li><a href=\"data/geoservices_CH.csv\">geoservices_CH.csv</a> – one row per service and layer (<a href=\"data/geoservices_CH.parquet\">Parquet</a>)</li><li><a href=\"data/geodata_CH.csv\">geodata_CH.csv</a> – one row per dataset with WMS, WMTS and WFS links (<a href=\"data/geodata_CH.parquet\">Parquet</a>)</li><li><a href=\"data/geoservices_stats_CH.csv\">geoservices_stats_CH.csv</a> – quality statistics per provider</li><li><a href=\"https://github.com/davidoesch/geoservice_harvester_poc/blob/main/sources.csv\">sources.csv</a> – all validated service endpoints</li></ul>",
        "A service is missing or broken? Add it to <code>sources.csv</code> with a pull request or open an <a href=\"https://github.com/davidoesch/geoservice_harvester_poc/issues\">issue</a>. Services with problems in the last run: <a href=\"https://github.com/davidoesch/geoservice_harvester_poc/blob/main/ISSUES.md\">ISSUES.md</a>."
      ],
      footerIssues: "Services with issues", footerBase: "Basemap © swisstopo",
      updated: (d) => `Updated: ${d}`, theme: "Toggle colour scheme", qgisDone: "QGIS layer file downloaded – drag it into QGIS.", arcgisDone: "ArcGIS Pro layer file downloaded – drag it onto the map.",
      mapLabel: "Map of Switzerland"
    }
  };

  // Multilingual topic synonyms (normalised forms). A query term that starts
  // with one of the variants expands to the whole group.
  const SYNONYMS = [
    ["biene", "imker", "abeille", "rucher", "apicult", "apicol", "apiar", "bees", "beehive"],
    ["wald", "walder", "forst", "foret", "bosco", "boschi", "forest", "sylvi"],
    ["baum", "baume", "arbre", "albero", "alberi", "tree"],
    ["gewasser", "fluss", "bach", "riviere", "cours", "fiume", "torrent", "river", "stream"],
    ["see", "seen", "lac", "lacs", "lago", "laghi", "lake"],
    ["grundwasser", "souterrain", "sotterrane", "groundwater", "aquifer", "nappe"],
    ["larm", "bruit", "rumore", "noise", "sonore"],
    ["naturgefahr", "gefahrenkart", "gefahrenzon", "danger", "pericol", "hazard"],
    ["lawine", "avalanche", "valanga", "valanghe"],
    ["hochwasser", "uberschwemm", "uberflut", "inondation", "crue", "alluvion", "esondazion", "flood"],
    ["rutsch", "glissement", "frana", "frane", "landslide", "sturz", "eboulement"],
    ["solar", "sonnenenergie", "photovolt", "fotovolt", "solaire", "solare"],
    ["velo", "fahrrad", "radweg", "radroute", "cyclable", "cycliste", "ciclabil", "bicicl", "bicycle", "bike", "cycling"],
    ["wanderweg", "wandern", "randonnee", "pedestre", "escursion", "hiking", "footpath"],
    ["gebaude", "batiment", "edific", "building"],
    ["parkplatz", "parkier", "parkhaus", "parking", "stationnement", "posteggi", "parcheggi"],
    ["schule", "schul", "ecole", "scolaire", "scuola", "scolast", "school"],
    ["naturschutz", "schutzgebiet", "reservat", "reserve", "riserva", "protett", "protected", "biotop"],
    ["jagd", "chasse", "caccia", "hunting"],
    ["wildtier", "wildruhe", "faune", "fauna", "wildlife"],
    ["landwirtschaft", "agricol", "agricult", "farming", "fruchtfolge"],
    ["boden", "pedolog", "suolo", "soil"],
    ["geolog", "gestein", "geotop"],
    ["kataster", "cadastre", "catasto", "parzelle", "parcelle", "particell", "liegenschaft", "grundstuck", "cadastral"],
    ["nutzungsplan", "zonenplan", "bauzone", "affectation", "azzonamento", "zoning", "landuse"],
    ["haltestelle", "fermata", "arret", "bus", "tram", "transport"],
    ["strasse", "route", "strada", "road", "street"],
    ["energie", "energia", "energy"],
    ["erdwarm", "geotherm", "geotermi", "warmepump", "sonde"],
    ["belastet", "altlast", "pollue", "inquinat", "contaminat"],
    ["orthofoto", "orthophoto", "ortofoto", "luftbild", "aerial", "swissimage", "aerienne"],
    ["hohenkurv", "hohenmodell", "relief", "altitude", "terrain", "elevation", "dtm", "dom"],
    ["denkmal", "kulturgut", "patrimoine", "monument", "culturali", "heritage", "archaolog", "archeolog", "ortsbild", "isos"],
    ["klima", "climat", "clima", "climate", "hitze", "chaleur", "calore"],
    ["bevolkerung", "einwohner", "population", "popolazione", "demograph"],
    ["grenze", "limite", "confine", "boundar", "border"],
    ["adresse", "indirizz", "address"],
    ["neophyt", "neofit", "invasiv"],
    ["spielplatz", "jeux", "giochi", "playground"],
    ["abfall", "entsorgung", "dechet", "rifiut", "waste", "recycling", "sammelstelle"],
    ["abwasser", "kanalisation", "usees", "reflue", "wastewater", "sewer", "klaranlage"],
    ["strom", "elektri", "electri", "elettric", "hochspannung"],
    ["antenne", "mobilfunk", "telephonie", "antenna"],
    ["erdbeben", "seism", "sismic", "earthquake", "mikrozon"],
    ["reben", "rebbau", "rebberg", "vigne", "viticult", "vigna", "viticol", "vineyard"],
    ["schnee", "neige", "neve", "snow"],
    ["gletscher", "glacier", "ghiacciai", "ghiacciaio"],
    ["tourismus", "tourisme", "turismo", "tourism"],
    ["gesundheit", "spital", "hopital", "ospedal", "sante", "health"],
    ["unfall", "unfalle", "accident", "incident"],
    ["verkehr", "trafic", "traffico", "traffic"],
    ["eisenbahn", "ferroviaire", "ferrovi", "railway"],
    ["trinkwasser", "wasserversorgung", "potable", "potabil", "drinking"],
    ["friedhof", "cimetiere", "cimitero", "cemetery"]
  ];
  const STOPWORDS = new Set(("der die das und oder von vom im in am an zu mit fur des dem den ein eine " +
    "le la les de du des et ou en au aux un une pour sur " +
    "il lo gli di da del della dei e o per " +
    "the of and or in for a an to on").split(" "));

  // ------------------------------------------------------------------- state
  const state = {
    lang: "de",
    q: "",
    kinds: new Set(),
    types: new Set(),
    region: "",
    owner: "",
    shown: PAGE_SIZE,
    results: [],
    selection: [],           // dataset indices
    layerState: new Map(),   // index -> {visible, opacity, status, legend}
    coverageMode: "results",
    basemap: "grau"
  };
  let catalog = null;       // raw catalog
  let D = [];               // dataset objects
  let owners = [];
  let services = [];
  let regionsGeo = null;
  let map = null;
  let idIndex = new Map();  // stable id -> dataset index

  // ----------------------------------------------------------------- helpers
  const $ = (sel, root = document) => root.querySelector(sel);
  const fmt = (n) => new Intl.NumberFormat(state.lang === "en" ? "en-GB" : state.lang + "-CH").format(n);
  const T = (key, ...args) => {
    const v = (I18N[state.lang] && I18N[state.lang][key]) ?? I18N.de[key];
    return typeof v === "function" ? v(...args) : v;
  };
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const store = {
    get(k) { try { return localStorage.getItem("gh." + k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem("gh." + k, v); } catch (e) { /* ignore */ } }
  };

  function norm(s) {
    return String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/ß/g, "ss").replace(/ae/g, "a").replace(/oe/g, "o").replace(/ue/g, "u")
      .replace(/[^a-z0-9]+/g, " ").trim();
  }

  function fnv(str) {
    let h = 0x811c9dc5;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 0x01000193);
    }
    return (h >>> 0).toString(36);
  }

  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => { el.hidden = true; }, 3200);
  }

  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch (e) {
      const ta = document.createElement("textarea");
      ta.value = text; document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); } catch (e2) { /* ignore */ }
      ta.remove();
    }
    toast(T("copied"));
  }

  function download(name, text, mime) {
    const blob = new Blob([text], { type: mime });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }

  function slug(s) {
    return norm(s).replace(/\s+/g, "-").slice(0, 40) || "auswahl";
  }

  function appendParams(url, params) {
    const sep = url.includes("?") ? (/[?&]$/.test(url) ? "" : "&") : "?";
    return url + sep + Object.entries(params).map(([k, v]) => k + "=" + encodeURIComponent(v)).join("&");
  }

  function capabilitiesUrl(svc) {
    if (/\.xml($|\?)/i.test(svc.url) || /request=getcapabilities/i.test(svc.url)) return svc.url;
    return appendParams(svc.url, { SERVICE: svc.type, REQUEST: "GetCapabilities" });
  }

  // ------------------------------------------------------------ data model
  function ownerLabel(o, lang = state.lang) {
    return (o.label && (o.label[lang] || o.label.de)) || o.code;
  }
  function ownerShort(o) {
    if (o.kind === "canton") return o.region;
    if (o.kind === "principality") return "FL";
    if (o.kind === "city") return o.municipality || ownerLabel(o);
    if (o.kind === "federal") return T("kind_federal");
    return ownerLabel(o).split(" (")[0];
  }
  function filterKind(o) {
    return o.kind === "principality" ? "canton" : o.kind;
  }

  function buildModel() {
    owners = catalog.owners;
    services = catalog.services.map(([type, url]) => ({ type, url: String(url).trim() }));
    const strings = catalog.strings || [];
    const fields = catalog.fields;
    const idx = Object.fromEntries(fields.map((f, i) => [f, i]));
    const ownerHay = owners.map((o) => " " + norm([o.code, o.region, o.municipality,
      ...Object.values(o.label || {})].filter(Boolean).join(" ")));
    D = catalog.datasets.map((row, i) => {
      const o = row[idx.owner];
      const svcs = row[idx.services].map(([s, layer]) => ({ ...services[s], layer }));
      svcs.sort((a, b) => ["WMS", "WMTS", "WFS"].indexOf(a.type) - ["WMS", "WMTS", "WFS"].indexOf(b.type));
      const first = svcs[0] || { url: "", layer: "" };
      const tpl = (k) => {
        const v = row[idx[k]];
        return v >= 0 && strings[v] ? strings[v].replaceAll("{L}", first.layer) : "";
      };
      const d = {
        i, o, owner: owners[o],
        title: row[idx.title] || first.layer,
        abstract: row[idx.abstract] || "",
        keywords: row[idx.keywords] || "",
        bbox: row[idx.bbox],
        legend: tpl("legend"),
        metadata: tpl("metadata"),
        group: row[idx.group] >= 0 ? (strings[row[idx.group]] || "") : "",
        regions: row[idx.regions],
        services: svcs,
        types: [...new Set(svcs.map((s) => s.type))]
      };
      d.id = fnv(d.owner.code + "|" + first.url + "|" + first.layer);
      d._t = " " + norm(d.title);
      d._k = " " + norm(d.keywords);
      d._g = " " + norm(d.group);
      d._a = " " + norm(d.abstract);
      d._o = ownerHay[o];
      return d;
    });
    idIndex = new Map(D.map((d) => [d.id, d.i]));
  }

  // ---------------------------------------------------------------- search
  function expandTerms(q) {
    const terms = norm(q).split(" ").filter((t) => t && !STOPWORDS.has(t));
    // synonyms go through the same normalisation as the indexed text
    // (e.g. "aerienne" -> "arienne")
    if (!expandTerms.groups) expandTerms.groups = SYNONYMS.map((g) => [...new Set(g.map(norm))]);
    return terms.map((t) => {
      const variants = [{ v: t, w: 1 }];
      for (const group of expandTerms.groups) {
        const hit = group.some((v) => t === v || (v.length >= 4 && t.startsWith(v)) || (t.length >= 4 && v.startsWith(t)));
        if (hit) {
          for (const v of group) {
            // synonyms only match at the start of a word ("bees" must not
            // match "retombees"); the user's own term may match anywhere
            if (v !== t) variants.push({ v, w: 0.8, ws: true });
          }
        }
      }
      return variants;
    });
  }

  function fieldScore(d, v, wordStart) {
    const short = wordStart || v.length <= 3;
    const ws = " " + v;
    if (d._t.includes(ws)) return 12 + (d._t === ws ? 6 : 0);
    let best = (!short && d._t.includes(v)) ? 8 : 0;
    const k = d._k.includes(ws) ? 6 : (!short && d._k.includes(v)) ? 4 : 0;
    const o = d._o.includes(ws) ? 5 : 0;
    const g = d._g.includes(ws) ? 4 : (!short && d._g.includes(v)) ? 2.5 : 0;
    const a = d._a.includes(ws) ? 3 : (!short && d._a.includes(v)) ? 1.5 : 0;
    best = Math.max(best, k, o, g, a);
    return best;
  }

  function passesFilters(d) {
    const o = d.owner;
    if (state.kinds.size && !state.kinds.has(filterKind(o))) return false;
    if (state.types.size && !d.types.some((t) => state.types.has(t))) return false;
    if (state.owner && o.code !== state.owner) return false;
    if (state.region) {
      const r = state.region;
      if (o.kind === "federal") return false;
      if (o.kind === "intercantonal") return d.regions ? d.regions.includes(r) : true;
      if (o.region !== r && o.canton !== r) return false;
    }
    return true;
  }

  function runSearch() {
    const groups = expandTerms(state.q);
    const out = [];
    if (!groups.length) {
      if (state.kinds.size || state.types.size || state.region || state.owner) {
        for (const d of D) if (passesFilters(d)) out.push({ d, s: 0 });
        out.sort((a, b) => a.d.o - b.d.o || a.d.title.localeCompare(b.d.title));
      }
    } else {
      for (const d of D) {
        let total = 0;
        for (const g of groups) {
          let best = 0;
          for (const { v, w, ws } of g) {
            const s = w * fieldScore(d, v, ws);
            if (s > best) best = s;
          }
          if (!best) { total = 0; break; }
          total += best;
        }
        if (total && passesFilters(d)) out.push({ d, s: total });
      }
      out.sort((a, b) => b.s - a.s || (a.d.types[0] === "WFS") - (b.d.types[0] === "WFS") || a.d.title.length - b.d.title.length);
    }
    state.results = out.map((r) => r.d);
    state.shown = PAGE_SIZE;
  }

  // --------------------------------------------------------------- coverage
  function computeCoverage(list) {
    const cov = {};
    let national = 0;
    const add = (code, key) => {
      if (!code) return;
      const c = cov[code] || (cov[code] = { own: 0, inter: 0, city: 0 });
      c[key]++;
    };
    for (const d of list) {
      const o = d.owner;
      if (o.kind === "canton" || o.kind === "principality") add(o.region, "own");
      else if (o.kind === "city") add(o.region, "city");
      else if (o.kind === "intercantonal") (d.regions || CANTONS).forEach((c) => add(c, "inter"));
      else if (o.kind === "federal") national++;
      else if (o.region) add(o.region, "own");
    }
    let cantons = 0, cities = 0, inter = 0;
    for (const [code, c] of Object.entries(cov)) {
      if (CANTONS.includes(code) && (c.own + c.inter) > 0) cantons++;
      if (code.startsWith("CITY_") && c.city > 0) cities++;
    }
    inter = list.filter((d) => d.owner.kind === "intercantonal").length;
    return { cov, national, cantons, cities, inter };
  }

  function coverageList() {
    if (state.coverageMode === "selection") return state.selection.map((i) => D[i]);
    if (!state.q && !state.kinds.size && !state.types.size && !state.region && !state.owner) return D;
    return state.results;
  }

  function binOf(n) {
    let b = -1;
    BINS.forEach((lo, i) => { if (n >= lo) b = i; });
    return b;
  }

  // ------------------------------------------------------------------- map
  let coverageLayer, cityLayer, highlightLayer, baseLayers = {};
  let coverage = { cov: {} };
  let hoverCode = null;
  const dataLayers = new Map(); // dataset index -> ol layer
  let hatch = null;

  function makeHatch() {
    const c = document.createElement("canvas");
    c.width = c.height = 8;
    const ctx = c.getContext("2d");
    ctx.fillStyle = "rgba(243,242,238,0.55)";
    ctx.fillRect(0, 0, 8, 8);
    ctx.strokeStyle = "rgba(120,118,110,0.55)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(0, 8); ctx.lineTo(8, 0);
    ctx.moveTo(-2, 2); ctx.lineTo(2, -2);
    ctx.moveTo(6, 10); ctx.lineTo(10, 6);
    ctx.stroke();
    return ctx.createPattern(c, "repeat");
  }

  function hexA(hex, a) {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
  }

  const styleCache = new Map();
  function regionStyle(feature) {
    const code = feature.get("code");
    const isCity = code.startsWith("CITY_");
    const c = coverage.cov[code] || { own: 0, inter: 0, city: 0 };
    const n = isCity ? c.city : c.own + c.inter;
    const bin = binOf(n);
    const hover = hoverCode === code;
    const sel = state.coverageMode === "selection" && state.selection.length > 0;
    const key = [isCity, bin, hover, sel, state.region === code].join("|");
    if (styleCache.has(key)) return styleCache.get(key);
    let style;
    const alpha = sel ? 0.28 : 0.62;
    if (isCity) {
      style = bin < 0 ? null : new ol.style.Style({
        fill: new ol.style.Fill({ color: hexA(RAMP[bin], Math.min(1, alpha + 0.15)) }),
        stroke: new ol.style.Stroke({ color: hover ? "#0b0b0b" : "#0d366b", width: hover ? 3 : 2 }),
        zIndex: 3
      });
    } else {
      style = new ol.style.Style({
        fill: new ol.style.Fill({ color: bin < 0 ? (sel ? "rgba(0,0,0,0)" : hatch) : hexA(RAMP[bin], alpha) }),
        stroke: new ol.style.Stroke({
          color: hover || state.region === code ? "#0b0b0b" : "rgba(13,54,107,0.55)",
          width: hover || state.region === code ? 2.5 : 1
        }),
        zIndex: hover ? 2 : 1
      });
      if (bin < 0 && sel) {
        style = [style, new ol.style.Style({ fill: new ol.style.Fill({ color: hatch }) })];
      }
    }
    styleCache.set(key, style);
    return style;
  }

  function decodeRegion(polys, q) {
    return polys.map((rings) => rings.map((flat) => {
      const pts = [];
      let x = 0, y = 0;
      for (let i = 0; i < flat.length; i += 2) {
        x += flat[i]; y += flat[i + 1];
        pts.push([x * q, y * q]);
      }
      return pts;
    }));
  }

  function regionLabel(code) {
    if (code === "LI") return ownerLabel(owners.find((o) => o.code === "FL_LI") || { code: "Liechtenstein", label: { de: "Fürstentum Liechtenstein" } });
    const o = owners.find((x) => x.region === code && (x.kind === "canton" || x.kind === "city"));
    return o ? ownerLabel(o) : code;
  }

  function initMap() {
    proj4.defs("EPSG:2056", "+proj=somerc +lat_0=46.9524055555556 +lon_0=7.43958333333333 +k_0=1 +x_0=2600000 +y_0=1200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs +type=crs");
    proj4.defs("EPSG:21781", "+proj=somerc +lat_0=46.9524055555556 +lon_0=7.43958333333333 +k_0=1 +x_0=600000 +y_0=200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs +type=crs");
    ol.proj.proj4.register(proj4);
    const lv95 = ol.proj.get("EPSG:2056");
    lv95.setExtent([2420000, 1030000, 2900000, 1350000]);
    hatch = makeHatch();

    const grid = new ol.tilegrid.WMTS({
      origin: [2420000, 1350000], resolutions: SWISSTOPO_RES,
      matrixIds: SWISSTOPO_RES.map((_, i) => String(i))
    });
    const swisstopo = (id) => new ol.layer.Tile({
      visible: false,
      source: new ol.source.WMTS({
        url: `https://wmts.geo.admin.ch/1.0.0/${id}/default/current/2056/{TileMatrix}/{TileCol}/{TileRow}.jpeg`,
        tileGrid: grid, projection: lv95, layer: id, matrixSet: "2056", style: "default",
        requestEncoding: "REST", attributions: '© <a href="https://www.swisstopo.admin.ch" target="_blank" rel="noopener">swisstopo</a>'
      })
    });
    baseLayers = {
      grau: swisstopo("ch.swisstopo.pixelkarte-grau"),
      farbe: swisstopo("ch.swisstopo.pixelkarte-farbe"),
      luftbild: swisstopo("ch.swisstopo.swissimage")
    };

    const covSrc = new ol.source.Vector();
    const citySrc = new ol.source.Vector();
    const q = regionsGeo.quantisation || 10;
    for (const [code, polys] of Object.entries(regionsGeo.regions)) {
      if (code === "CH") continue;
      const f = new ol.Feature({ geometry: new ol.geom.MultiPolygon(decodeRegion(polys, q)), code });
      (code.startsWith("CITY_") ? citySrc : covSrc).addFeature(f);
    }
    coverageLayer = new ol.layer.Vector({ source: covSrc, style: regionStyle, zIndex: 10 });
    cityLayer = new ol.layer.Vector({ source: citySrc, style: regionStyle, zIndex: 11 });
    highlightLayer = new ol.layer.Vector({
      source: new ol.source.Vector(), zIndex: 1000,
      style: new ol.style.Style({ stroke: new ol.style.Stroke({ color: "#d03b3b", width: 2, lineDash: [6, 4] }) })
    });

    map = new ol.Map({
      target: "map",
      layers: [...Object.values(baseLayers), coverageLayer, cityLayer, highlightLayer],
      view: new ol.View({ projection: lv95, center: [2660000, 1190000], resolution: 650, extent: [2380000, 1000000, 2940000, 1380000], showFullExtent: true }),
      controls: ol.control.defaults.defaults({ rotate: false, attributionOptions: { collapsible: true } })
    });
    fitExtent(CH_EXTENT, false);
    setBasemap(state.basemap);

    const tip = $("#map-tooltip");
    map.on("pointermove", (evt) => {
      if (evt.dragging) return;
      let code = null;
      map.forEachFeatureAtPixel(evt.pixel, (f) => { code = f.get("code"); return true; },
        { layerFilter: (l) => l === cityLayer || l === coverageLayer });
      if (code !== hoverCode) {
        hoverCode = code;
        styleCache.clear();
        coverageLayer.changed(); cityLayer.changed();
      }
      if (!code) { tip.hidden = true; map.getTargetElement().style.cursor = ""; return; }
      const c = coverage.cov[code] || { own: 0, inter: 0, city: 0 };
      const lines = [];
      if (code.startsWith("CITY_")) { if (c.city) lines.push(T("tipCity", c.city)); }
      else {
        if (c.own) lines.push(T("tipOwn", c.own));
        if (c.inter) lines.push(T("tipInter", c.inter));
      }
      if (!lines.length) lines.push(T("tipNone"));
      if (state.coverageMode === "results") lines.push(`<span class="muted">${esc(T("tipClick"))}</span>`);
      tip.innerHTML = `<strong>${esc(regionLabel(code))}</strong>${lines.map((l) => `<div>${l.startsWith("<") ? l : esc(l)}</div>`).join("")}`;
      tip.hidden = false;
      const [x, y] = evt.pixel;
      const mapEl = map.getTargetElement();
      const w = mapEl.clientWidth;
      tip.style.left = Math.min(x + 14, w - 270) + "px";
      tip.style.top = (y + 14 + mapEl.offsetTop) + "px";
      mapEl.style.cursor = state.coverageMode === "results" ? "pointer" : "";
    });
    map.getViewport().addEventListener("mouseleave", () => {
      tip.hidden = true;
      if (hoverCode) { hoverCode = null; styleCache.clear(); coverageLayer.changed(); cityLayer.changed(); }
    });
    map.on("singleclick", (evt) => {
      if (state.coverageMode !== "results") return;
      let code = null;
      map.forEachFeatureAtPixel(evt.pixel, (f) => { code = f.get("code"); return true; },
        { layerFilter: (l) => l === cityLayer || l === coverageLayer });
      if (!code) return;
      if (code.startsWith("CITY_")) {
        state.owner = state.owner === code ? "" : code;
      } else {
        state.region = state.region === code ? "" : code;
        state.owner = "";
        $("#region-filter").value = state.region;
      }
      update();
    });
  }

  function setBasemap(name) {
    state.basemap = name;
    store.set("basemap", name);
    for (const [k, l] of Object.entries(baseLayers)) l.setVisible(k === name);
  }

  function refreshCoverage() {
    coverage = computeCoverage(coverageList());
    styleCache.clear();
    if (coverageLayer) { coverageLayer.changed(); cityLayer.changed(); }
    renderLegend();
  }

  function renderLegend() {
    const el = $("#map-legend");
    el.hidden = state.coverageMode === "off";
    const labels = ["1", "2–3", "4–9", "10+"];
    let html = `<span class="item"><span class="swatch nodata"></span>${esc(T("legendNoData"))}</span>`;
    html += `<span class="item">${esc(T("legendCount"))}</span>`;
    RAMP.forEach((c, i) => { html += `<span class="item"><span class="swatch" style="background:${c}"></span>${labels[i]}</span>`; });
    html += `<span class="item"><span class="swatch city"></span>${esc(T("legendCity"))}</span>`;
    const notes = [];
    if (coverage.national) notes.push(T("national", coverage.national));
    notes.push(state.coverageMode === "results" ? T("legendClick") : T("legendSelection"));
    html += `<span class="legend-note">${esc(notes.join(" · "))}</span>`;
    el.innerHTML = html;
  }

  function bboxToLv95(b) {
    try {
      return ol.proj.transformExtent(b, "EPSG:4326", "EPSG:2056");
    } catch (e) { return null; }
  }

  function highlightBbox(d) {
    const src = highlightLayer.getSource();
    src.clear();
    if (!d || !d.bbox) return;
    const e = bboxToLv95(d.bbox);
    if (e) src.addFeature(new ol.Feature(ol.geom.Polygon.fromExtent(e)));
  }

  // The map may be hidden (mobile list tab): fitting a 0x0 map gives a
  // broken view, so fits are deferred until the map is visible.
  let pendingFit = null;
  function mapVisible() {
    const el = map && map.getTargetElement();
    return !!el && el.offsetWidth > 0 && el.offsetHeight > 0;
  }
  function fitExtent(ext, animate = true) {
    if (!map) return;
    if (!mapVisible()) { pendingFit = ext; return; }
    map.updateSize();
    map.getView().fit(ext, { padding: [30, 30, 30, 30], maxZoom: 22, duration: animate ? 400 : 0 });
  }
  function onMapShown() {
    if (!map) return;
    map.updateSize();
    if (pendingFit) { const e = pendingFit; pendingFit = null; fitExtent(e, false); }
  }

  function zoomToDatasets(list) {
    const ext = ol.extent.createEmpty();
    list.forEach((d) => { if (d.bbox) { const e = bboxToLv95(d.bbox); if (e) ol.extent.extend(ext, e); } });
    if (ol.extent.isEmpty(ext)) return;
    fitExtent(ext);
  }

  // ---------------------------------------------- data layers on the map
  function pickService(d, order = ["WMS", "WMTS", "WFS"]) {
    for (const t of order) {
      const s = d.services.find((x) => x.type === t);
      if (s) return s;
    }
    return null;
  }

  function isFederalInternal(svc) {
    return /^https:\/\/(wms|wmts)\.geo\.admin\.ch\//.test(svc.url);
  }

  function setStatus(i, status) {
    const ls = state.layerState.get(i);
    if (!ls || ls.status === status) return;
    ls.status = status;
    const el = document.querySelector(`.sel-item[data-i="${i}"] .status`);
    if (el) {
      el.className = "status " + ({ ok: "ok", err: "err", cors: "err", loading: "loading", wfs: "ok" }[status] || "");
      el.textContent = T("st_" + status);
    }
  }

  // Extent of a dataset (with a margin) so that a layer only requests images
  // while its area is in view - important with many layers on the map.
  function layerExtent(i) {
    const d = D[i];
    const e = d && d.bbox ? bboxToLv95(d.bbox) : null;
    if (!e || !e.every(Number.isFinite)) return undefined;
    const pad = Math.max(e[2] - e[0], e[3] - e[1]) * 0.1 + 500;
    return ol.extent.buffer(e, pad);
  }

  function makeWmsLayer(i, svc, ls) {
    const attempts = [["EPSG:2056", "1.3.0"], ["EPSG:3857", "1.3.0"], ["EPSG:2056", "1.1.1"], ["EPSG:4326", "1.1.1"]];
    let n = 0;
    const layer = new ol.layer.Image({ opacity: ls.opacity, visible: ls.visible, extent: layerExtent(i) });
    const setSource = () => {
      const [crs, version] = attempts[n];
      const src = new ol.source.ImageWMS({
        url: svc.url, projection: crs, ratio: 1,
        params: { LAYERS: svc.layer, FORMAT: "image/png", TRANSPARENT: true, VERSION: version, STYLES: "" }
      });
      let loaded = false;
      src.on("imageloadstart", () => { if (!loaded) setStatus(i, "loading"); });
      src.on("imageloadend", () => { loaded = true; setStatus(i, "ok"); });
      src.on("imageloaderror", () => {
        if (loaded) return;
        if (++n < attempts.length) setSource();
        else setStatus(i, "err");
      });
      layer.setSource(src);
    };
    setSource();
    return layer;
  }

  const wmtsCapsCache = new Map();
  async function wmtsCapabilities(url) {
    if (!wmtsCapsCache.has(url)) {
      wmtsCapsCache.set(url, fetch(url).then((r) => {
        if (!r.ok) throw new Error(r.status);
        return r.text();
      }).then((txt) => new ol.format.WMTSCapabilities().read(txt)));
    }
    return wmtsCapsCache.get(url);
  }

  function chooseMatrixSet(caps, layerId) {
    const layer = (caps.Contents.Layer || []).find((l) => l.Identifier === layerId);
    if (!layer) return null;
    const links = (layer.TileMatrixSetLink || []).map((l) => l.TileMatrixSet);
    const sets = caps.Contents.TileMatrixSet || [];
    const crsOf = (id) => ((sets.find((s) => s.Identifier === id) || {}).SupportedCRS || "");
    return links.find((id) => /2056/.test(crsOf(id))) || links.find((id) => /3857|900913/.test(crsOf(id))) || links[0] || null;
  }

  function makeWmtsLayer(i, svc, ls) {
    const layer = new ol.layer.Tile({ opacity: ls.opacity, visible: ls.visible, extent: layerExtent(i) });
    setStatus(i, "loading");
    wmtsCapabilities(capabilitiesUrl(svc)).then((caps) => {
      const matrixSet = chooseMatrixSet(caps, svc.layer);
      const opts = ol.source.WMTS.optionsFromCapabilities(caps, { layer: svc.layer, matrixSet });
      if (!opts) throw new Error("layer not found");
      const src = new ol.source.WMTS(opts);
      src.on("tileloadend", () => setStatus(i, "ok"));
      src.on("tileloaderror", () => { if (state.layerState.get(i)?.status !== "ok") setStatus(i, "err"); });
      layer.setSource(src);
    }).catch(() => setStatus(i, "cors"));
    return layer;
  }

  function makeWfsLayer(i, svc, ls) {
    const src = new ol.source.Vector();
    const layer = new ol.layer.Vector({
      source: src, opacity: ls.opacity, visible: ls.visible,
      style: new ol.style.Style({
        stroke: new ol.style.Stroke({ color: "#c2410c", width: 1.6 }),
        fill: new ol.style.Fill({ color: "rgba(234,104,52,0.18)" }),
        image: new ol.style.Circle({ radius: 4, fill: new ol.style.Fill({ color: "#c2410c" }), stroke: new ol.style.Stroke({ color: "#fff", width: 1 }) })
      })
    });
    setStatus(i, "loading");
    const tryFormats = ["application/json", "geojson", "json"];
    const requests = [];
    for (const f of tryFormats) {
      requests.push({ SERVICE: "WFS", REQUEST: "GetFeature", VERSION: "2.0.0", TYPENAMES: svc.layer, COUNT: 3000, SRSNAME: "EPSG:2056", OUTPUTFORMAT: f });
    }
    // MapServer and older servers: WFS 1.1.0 parameter names
    requests.push({ SERVICE: "WFS", REQUEST: "GetFeature", VERSION: "1.1.0", TYPENAME: svc.layer, MAXFEATURES: 3000, SRSNAME: "EPSG:2056", OUTPUTFORMAT: "geojson" });
    requests.push({ SERVICE: "WFS", REQUEST: "GetFeature", VERSION: "1.1.0", TYPENAME: svc.layer, MAXFEATURES: 3000, SRSNAME: "EPSG:2056", OUTPUTFORMAT: "application/json" });
    const attempt = async () => {
      for (const params of requests) {
        const url = appendParams(svc.url, params);
        try {
          const r = await fetch(url);
          if (!r.ok) continue;
          const json = await r.json();
          if (!json || !Array.isArray(json.features)) continue;
          const sample = JSON.stringify(json.features.slice(0, 1)).match(/-?\d+\.?\d*/g) || [];
          const big = sample.some((v) => Math.abs(parseFloat(v)) > 1000);
          const feats = new ol.format.GeoJSON().readFeatures(json, {
            dataProjection: big ? "EPSG:2056" : "EPSG:4326", featureProjection: "EPSG:2056"
          });
          src.addFeatures(feats);
          setStatus(i, "wfs");
          return;
        } catch (e) { /* CORS or parse error: try next format */ }
      }
      setStatus(i, "cors");
    };
    attempt();
    return layer;
  }

  function syncMapLayers() {
    if (!map) return;
    // remove layers no longer selected
    for (const [i, layer] of dataLayers) {
      if (!state.selection.includes(i)) { map.removeLayer(layer); dataLayers.delete(i); }
    }
    state.selection.forEach((i, pos) => {
      const ls = state.layerState.get(i);
      let layer = dataLayers.get(i);
      if (!layer) {
        const d = D[i];
        const svc = pickService(d);
        if (!svc) return;
        layer = svc.type === "WMS" ? makeWmsLayer(i, svc, ls) : svc.type === "WMTS" ? makeWmtsLayer(i, svc, ls) : makeWfsLayer(i, svc, ls);
        dataLayers.set(i, layer);
        map.addLayer(layer);
      }
      layer.setZIndex(100 + pos);
      layer.setOpacity(ls.opacity);
      layer.setVisible(ls.visible);
    });
  }

  // ------------------------------------------------------------- selection
  function isSelected(i) { return state.selection.includes(i); }

  function addToSelection(indices, { fit = false } = {}) {
    let added = 0;
    for (const i of indices) {
      if (isSelected(i)) continue;
      if (state.selection.length >= MAX_SELECTION) { toast(T("tooMany", MAX_SELECTION)); break; }
      state.selection.push(i);
      state.layerState.set(i, { visible: true, opacity: 0.85, status: "loading", legend: false });
      added++;
    }
    if (added && state.coverageMode === "results") setCoverageMode("selection");
    selectionChanged();
    if (fit || state.selection.length === added) zoomToDatasets(indices.map((i) => D[i]));
  }

  function removeFromSelection(i) {
    state.selection = state.selection.filter((x) => x !== i);
    state.layerState.delete(i);
    if (!state.selection.length && state.coverageMode === "selection") setCoverageMode("results");
    selectionChanged();
  }

  function selectionChanged() {
    syncMapLayers();
    renderSelection();
    refreshCoverage();
    updateCardButtons();
    writeHash();
  }

  function setCoverageMode(mode) {
    state.coverageMode = mode;
    document.querySelectorAll("#coverage-mode button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === mode)));
    if (coverageLayer) {
      coverageLayer.setVisible(mode !== "off");
      cityLayer.setVisible(mode !== "off");
    }
    refreshCoverage();
  }

  function renderSelection() {
    const list = $("#selection-list");
    const n = state.selection.length;
    $("#selection-count").textContent = n;
    const tabCount = $("#tab-map-count");
    tabCount.textContent = n; tabCount.hidden = !n;
    $("#selection-empty").hidden = n > 0;
    $("#export-row").hidden = n === 0;
    $("#clear-selection").hidden = n === 0;
    list.innerHTML = state.selection.slice().reverse().map((i) => {
      const d = D[i];
      const ls = state.layerState.get(i);
      const svc = pickService(d);
      const legendUrl = d.legend || (svc && svc.type === "WMS" ? appendParams(svc.url, { SERVICE: "WMS", REQUEST: "GetLegendGraphic", VERSION: "1.3.0", FORMAT: "image/png", LAYER: svc.layer, SLD_VERSION: "1.1.0" }) : "");
      const st = ls.status || "loading";
      return `<li class="sel-item" data-i="${i}">
        <input type="checkbox" ${ls.visible ? "checked" : ""} aria-label="${esc(d.title)}" data-act="vis">
        <div style="min-width:0">
          <div class="sel-title" title="${esc(d.title)}">${esc(d.title)}</div>
          <div class="sel-sub"><span>${esc(ownerShort(d.owner))} · ${esc(svc ? svc.type : "")}</span><span class="status ${st === "ok" || st === "wfs" ? "ok" : st === "loading" ? "loading" : "err"}">${esc(T("st_" + st))}</span></div>
        </div>
        <div class="sel-tools">
          ${legendUrl ? `<button type="button" data-act="legend" title="${esc(T("toggleLegend"))}" aria-label="${esc(T("toggleLegend"))}">▤</button>` : ""}
          <button type="button" data-act="zoom" title="${esc(T("zoomTo"))}" aria-label="${esc(T("zoomTo"))}">⌖</button>
          <button type="button" data-act="remove" title="${esc(T("remove"))}" aria-label="${esc(T("remove"))}">✕</button>
        </div>
        <input type="range" min="0" max="1" step="0.05" value="${ls.opacity}" aria-label="${esc(T("opacity"))}" data-act="opacity">
        ${ls.legend && legendUrl ? `<div class="sel-legend"><img src="${esc(legendUrl)}" alt="${esc(T("legend"))}" loading="lazy" onerror="this.parentNode.remove()"></div>` : ""}
      </li>`;
    }).join("");
    updateExports();
  }

  // ---------------------------------------------------------------- exports
  function encExt(s) {
    return String(s).replace(/\|/g, "%7C").replace(/,/g, "%2C").replace(/;/g, "%3B").replace(/@/g, "%40");
  }

  function lv95View(list) {
    let ext = null;
    list.forEach((d) => { if (d.bbox) { const e = bboxToLv95(d.bbox); if (e) ext = ext ? ol.extent.extend(ext, e) : e.slice(); } });
    if (!ext) return { center: [2660000, 1190000], z: 1 };
    const center = [Math.round((ext[0] + ext[2]) / 2), Math.round((ext[1] + ext[3]) / 2)];
    const need = Math.max((ext[2] - ext[0]) / 1100, (ext[3] - ext[1]) / 700, 0.1);
    let z = 0;
    MAPGEO_RES.forEach((r, i) => { if (r >= need) z = i; });
    return { center, z };
  }

  function mapGeoUrl(list) {
    const parts = [];
    const used = [];
    let skipped = 0;
    for (const d of list) {
      const svc = pickService(d, ["WMS", "WMTS"]);
      if (!svc) { skipped++; continue; }
      const ls = state.layerState.get(d.i) || { opacity: 1, visible: true };
      const id = isFederalInternal(svc) ? encExt(svc.layer) : `${svc.type}|${encExt(svc.type === "WMTS" ? capabilitiesUrl(svc) : svc.url)}|${encExt(svc.layer)}`;
      parts.push(`${id},${ls.visible ? "t" : "f"},${ls.opacity}`);
      used.push(d);
    }
    if (!parts.length) return { url: null, skipped };
    const { center, z } = lv95View(used);
    const lang = state.lang;
    const url = `https://map.geo.admin.ch/#/map?lang=${lang}&center=${center[0]},${center[1]}&z=${z}` +
      `&bgLayer=ch.swisstopo.pixelkarte-grau&layers=${encodeURIComponent(parts.join(";"))}`;
    return { url, skipped };
  }

  function updateExports() {
    const list = state.selection.map((i) => D[i]);
    const { url, skipped } = mapGeoUrl(list);
    const a = $("#open-mapgeo");
    if (url) { a.href = url; a.removeAttribute("aria-disabled"); a.hidden = false; }
    else { a.hidden = true; }
    const notes = [];
    if (skipped) notes.push(T("noteWfs", skipped));
    if (list.length > MANY_LAYERS) notes.push(T("noteMany"));
    const note = $("#export-note");
    note.textContent = notes.join(" ");
    note.hidden = !notes.length;
  }

  const xmlEsc = (s) => String(s).replace(/[<>&'"]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", "'": "&apos;", '"': "&quot;" }[c]));
  const SRS_2056 = `<srs><spatialrefsys><proj4>+proj=somerc +lat_0=46.9524055555556 +lon_0=7.43958333333333 +k_0=1 +x_0=2600000 +y_0=1200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs</proj4><srid>2056</srid><authid>EPSG:2056</authid><description>CH1903+ / LV95</description><projectionacronym>somerc</projectionacronym><ellipsoidacronym>EPSG:7004</ellipsoidacronym><geographicflag>false</geographicflag></spatialrefsys></srs>`;

  async function wmtsInfo(svc) {
    try {
      const caps = await wmtsCapabilities(capabilitiesUrl(svc));
      const layer = (caps.Contents.Layer || []).find((l) => l.Identifier === svc.layer) || {};
      const style = ((layer.Style || []).find((s) => s.isDefault) || (layer.Style || [])[0] || {}).Identifier || "default";
      const matrixSet = chooseMatrixSet(caps, svc.layer) || "";
      const set = (caps.Contents.TileMatrixSet || []).find((x) => x.Identifier === matrixSet) || {};
      const code = (String(set.SupportedCRS || "").match(/(\d{4,6})\s*$/) || [])[1];
      return { matrixSet, style, format: (layer.Format || ["image/png"])[0], crs: code ? "EPSG:" + (code === "900913" ? "3857" : code) : "EPSG:2056" };
    } catch (e) {
      return { matrixSet: "", style: "default", format: "image/png", crs: "EPSG:2056" };
    }
  }

  async function buildQlr(list, groupName) {
    const tree = [], layers = [];
    const stamp = Date.now().toString(36);
    for (let n = 0; n < list.length; n++) {
      const d = list[n];
      const svc = pickService(d);
      if (!svc) continue;
      const id = `geoharvester_${stamp}_${n}`;
      const url = svc.url.includes("&") ? encodeURIComponent(svc.url) : svc.url;
      let type = "raster", provider = "wms", source, crs = "EPSG:2056";
      if (svc.type === "WMS") {
        source = `contextualWMSLegend=0&crs=EPSG:2056&dpiMode=7&featureCount=10&format=image/png&layers=${encodeURIComponent(svc.layer)}&styles&url=${url}`;
      } else if (svc.type === "WMTS") {
        const info = await wmtsInfo(svc);
        crs = info.crs;
        const capUrl = capabilitiesUrl(svc);
        source = `contextualWMSLegend=0&crs=${info.crs}&dpiMode=7&featureCount=10&format=${info.format}&layers=${encodeURIComponent(svc.layer)}&styles=${encodeURIComponent(info.style)}&tileMatrixSet=${encodeURIComponent(info.matrixSet)}&url=${capUrl.includes("&") ? encodeURIComponent(capUrl) : capUrl}`;
      } else {
        type = "vector"; provider = "WFS";
        source = ` pagingEnabled='true' preferCoordinatesForWfsT11='false' restrictToRequestBBOX='1' srsname='EPSG:2056' typename='${svc.layer}' url='${svc.url}' version='auto'`;
      }
      const e = d.bbox ? bboxToLv95(d.bbox) : CH_EXTENT;
      const name = `${d.title} (${ownerShort(d.owner)})`;
      tree.push(`      <layer-tree-layer expanded="0" checked="Qt::Checked" id="${id}" name="${xmlEsc(name)}" source="${xmlEsc(source)}" providerKey="${provider}"/>`);
      layers.push(`    <maplayer type="${type}" hasScaleBasedVisibilityFlag="0" minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories">
      <extent><xmin>${Math.round(e[0])}</xmin><ymin>${Math.round(e[1])}</ymin><xmax>${Math.round(e[2])}</xmax><ymax>${Math.round(e[3])}</ymax></extent>
      <id>${id}</id>
      <datasource>${xmlEsc(source)}</datasource>
      <layername>${xmlEsc(name)}</layername>
      ${crs === "EPSG:2056" ? SRS_2056 : `<srs><spatialrefsys><authid>${crs}</authid></spatialrefsys></srs>`}
      <provider>${provider}</provider>
    </maplayer>`);
    }
    return `<!DOCTYPE qgis-layer-definition>
<qlr>
  <layer-tree-group expanded="1" checked="Qt::Checked" name="">
    <layer-tree-group expanded="1" checked="Qt::Checked" name="${xmlEsc(groupName)}">
${tree.join("\n")}
    </layer-tree-group>
  </layer-tree-group>
  <maplayers>
${layers.join("\n")}
  </maplayers>
</qlr>
`;
  }

  const lyrxTemplates = {};
  async function lyrxTemplate(type) {
    if (!lyrxTemplates[type]) {
      lyrxTemplates[type] = fetch(`templates/arcgispro_${type.toLowerCase()}_template.lyrx`).then((r) => {
        if (!r.ok) throw new Error("template " + type);
        return r.text();
      });
    }
    return lyrxTemplates[type];
  }

  async function buildLyrx(list) {
    const jsonStr = (s) => JSON.stringify(String(s)).slice(1, -1);
    let doc = null;
    const defs = [];
    for (let n = 0; n < list.length; n++) {
      const d = list[n];
      const svc = pickService(d);
      if (!svc) continue;
      const tpl = await lyrxTemplate(svc.type);
      const url = svc.type === "WMTS" ? capabilitiesUrl(svc) : svc.url;
      const name = `${d.title} (${ownerShort(d.owner)})`;
      const text = tpl.replaceAll("{{NAME}}", jsonStr(svc.layer)).replaceAll("{{TITLE}}", jsonStr(name))
        .replaceAll("{{SERVICELINK}}", jsonStr(url)).replaceAll("{{OWNER}}", jsonStr(d.owner.code));
      const parsed = JSON.parse(text);
      const def = parsed.layerDefinitions[0];
      def.name = name;
      def.uRI = `CIMPATH=geoharvester/layer_${n}.json`;
      if (svc.type === "WMTS") {
        const info = await wmtsInfo(svc);
        def.serviceConnection.style = info.style;
        def.serviceConnection.imageFormat = info.format;
        if (info.matrixSet) def.serviceConnection.tileMatrixSet = info.matrixSet;
      }
      defs.push(def);
      if (!doc) doc = parsed;
    }
    if (!doc) return null;
    doc.layers = defs.map((d) => d.uRI);
    doc.layerDefinitions = defs;
    return JSON.stringify(doc, null, 2);
  }

  async function exportQgis(list) {
    const text = await buildQlr(list, "GeoHarvester" + (state.q ? " – " + state.q : ""));
    download(`geoharvester-${slug(state.q || (list.length === 1 ? list[0].title : ""))}.qlr`, text, "application/xml");
    toast(T("qgisDone"));
  }

  async function exportArcgis(list) {
    const text = await buildLyrx(list);
    if (!text) return;
    download(`geoharvester-${slug(state.q || (list.length === 1 ? list[0].title : ""))}.lyrx`, text, "application/json");
    toast(T("arcgisDone"));
  }

  function exportCsv() {
    const rows = [["OWNER", "PROVIDER", "TITLE", "SERVICETYPES", "WMS", "WMTS", "WFS", "LAYER", "ABSTRACT", "KEYWORDS", "METADATA"]];
    for (const d of state.results) {
      const s = (t) => (d.services.find((x) => x.type === t) || {}).url || "";
      rows.push([d.owner.code, ownerLabel(d.owner), d.title, d.types.join(" "), s("WMS"), s("WMTS"), s("WFS"),
        (d.services[0] || {}).layer || "", d.abstract, d.keywords, d.metadata]);
    }
    const csv = rows.map((r) => r.map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`).join(",")).join("\r\n");
    download(`geoharvester-${slug(state.q)}.csv`, "﻿" + csv, "text/csv;charset=utf-8");
  }

  // ------------------------------------------------------------- rendering
  function renderResults() {
    const list = $("#results");
    const total = state.results.length;
    const hasCriteria = !!(state.q || state.kinds.size || state.types.size || state.region || state.owner);
    document.body.classList.toggle("has-query", hasCriteria);

    $("#results-count").textContent = hasCriteria ? T("results", total) : T("browse", D.length);
    const cov = computeCoverage(hasCriteria ? state.results : D);
    $("#coverage-summary").textContent = hasCriteria && total ? T("covSummary", cov.cantons, cov.cities, cov.national + cov.inter) : "";

    const addAll = $("#add-all");
    addAll.hidden = !hasCriteria || total < 2;
    addAll.textContent = total <= MAX_SELECTION ? T("addAll", total) : T("addAllCapped", MAX_SELECTION, total);
    addAll.onclick = () => {
      const before = state.selection.length;
      addToSelection(state.results.slice(0, MAX_SELECTION).map((d) => d.i), { fit: true });
      const added = state.selection.length - before;
      if (added > 1) toast(T("addedN", added));
    };
    $("#export-csv").hidden = !hasCriteria || !total;

    renderFacets(hasCriteria);

    const empty = $("#empty-state");
    if (!hasCriteria) {
      list.innerHTML = "";
      empty.innerHTML = `<h3>${esc(T("startTitle"))}</h3><p>${esc(T("startHint"))}</p>`;
      empty.hidden = false;
      $("#show-more").hidden = true;
      return;
    }
    if (!total) {
      list.innerHTML = "";
      empty.innerHTML = `<h3>${esc(T("noResults"))}</h3><p>${esc(T("noResultsHint"))}</p>`;
      empty.hidden = false;
      $("#show-more").hidden = true;
      return;
    }
    empty.hidden = true;
    list.innerHTML = state.results.slice(0, state.shown).map(cardHtml).join("");
    const rest = total - state.shown;
    const more = $("#show-more");
    more.hidden = rest <= 0;
    more.textContent = T("showMore", Math.min(rest, PAGE_SIZE));
  }

  function cardHtml(d) {
    const sel = isSelected(d.i);
    const map1 = mapGeoUrl([d]).url;
    const badges = d.types.map((t) => `<span class="badge badge-${t}">${t}</span>`).join("");
    const menu = [];
    d.services.forEach((s) => {
      menu.push(`<button type="button" data-act="copy" data-url="${esc(s.type === "WMTS" ? capabilitiesUrl(s) : s.url)}">${esc(T("copyUrl", s.type))}<small>${esc(s.layer)}</small></button>`);
      menu.push(`<a href="${esc(capabilitiesUrl(s))}" target="_blank" rel="noopener">${esc(T("openCap", s.type))}</a>`);
    });
    if (d.metadata) menu.push(`<a href="${esc(d.metadata)}" target="_blank" rel="noopener">${esc(T("metadata"))}</a>`);
    if (d.legend) menu.push(`<a href="${esc(d.legend)}" target="_blank" rel="noopener">${esc(T("legend"))}</a>`);
    const long = d.abstract.length > 160;
    return `<li class="card${sel ? " selected" : ""}" data-i="${d.i}">
      <div class="card-top">
        <h3 class="card-title">${esc(d.title)}</h3>
        <button type="button" class="add-btn" data-act="toggle" aria-pressed="${sel}" aria-label="${esc(T("addToMapLabel"))}: ${esc(d.title)}">${esc(sel ? T("onMap") : T("addToMap"))}</button>
      </div>
      <div class="card-meta"><span class="owner">${esc(ownerLabel(d.owner))}</span>${badges}${d.group ? `<span class="group-path" title="${esc(d.group)}">${esc(d.group)}</span>` : ""}</div>
      ${d.abstract ? `<p class="abstract${long ? " clamped" : ""}">${esc(d.abstract)}</p>` : ""}
      <div class="card-actions">
        ${map1 ? `<a class="link-btn" href="${esc(map1)}" target="_blank" rel="noopener">${esc(T("mapgeo"))} ↗</a>` : ""}
        <button type="button" class="link-btn" data-act="qgis">QGIS</button>
        <button type="button" class="link-btn" data-act="arcgis">ArcGIS Pro</button>
        ${long ? `<button type="button" class="link-btn" data-act="expand">${esc(T("more"))}</button>` : ""}
        <details class="more"><summary>${esc(T("moreMenu"))}</summary><div class="menu">${menu.join("")}</div></details>
      </div>
    </li>`;
  }

  function updateCardButtons() {
    document.querySelectorAll("#results .card").forEach((card) => {
      const i = +card.dataset.i;
      const sel = isSelected(i);
      card.classList.toggle("selected", sel);
      const btn = card.querySelector('[data-act="toggle"]');
      btn.setAttribute("aria-pressed", String(sel));
      btn.textContent = sel ? T("onMap") : T("addToMap");
    });
  }

  function renderFacets(hasCriteria) {
    const el = $("#facets");
    if (!hasCriteria || !state.results.length) { el.innerHTML = ""; return; }
    const counts = new Map();
    state.results.forEach((d) => counts.set(d.o, (counts.get(d.o) || 0) + 1));
    const top = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 16);
    if (top.length < 2 && !state.owner) { el.innerHTML = ""; return; }
    el.innerHTML = top.map(([o, n]) => {
      const ow = owners[o];
      const on = state.owner === ow.code;
      return `<button type="button" class="chip" data-owner="${esc(ow.code)}" aria-pressed="${on}" title="${esc(ownerLabel(ow))}">${esc(ownerShort(ow))} <span class="n">${fmt(n)}</span>${on ? " ✕" : ""}</button>`;
    }).join("");
  }

  function renderFilters() {
    const kinds = ["federal", "canton", "city", "intercantonal"];
    $("#kind-filter").innerHTML = kinds.map((k) => `<button type="button" class="chip" data-kind="${k}" aria-pressed="${state.kinds.has(k)}">${esc(T("kind_" + k))}</button>`).join("");
    $("#type-filter").innerHTML = ["WMS", "WMTS", "WFS"].map((t) => `<button type="button" class="chip" data-type="${t}" aria-pressed="${state.types.has(t)}">${t}</button>`).join("");
    const regions = CANTONS.map((c) => [c, regionLabel(c)]).concat([["LI", regionLabel("LI")]])
      .sort((a, b) => a[1].localeCompare(b[1], state.lang));
    $("#region-filter").innerHTML = `<option value="">${esc(T("allRegions"))}</option>` +
      regions.map(([c, l]) => `<option value="${c}" ${state.region === c ? "selected" : ""}>${esc(l)}</option>`).join("");
    $("#basemap").innerHTML = ["grau", "farbe", "luftbild", "none"].map((b) => `<option value="${b}" ${state.basemap === b ? "selected" : ""}>${esc(T("bg_" + b))}</option>`).join("");
    $("#topics").innerHTML = T("topics").map((t) => `<button type="button" data-topic="${esc(t)}">${esc(t)}</button>`).join("");
  }

  function renderInfo() {
    $("#about-text").innerHTML = T("about").map((p) => `<p>${p}</p>`).join("");
    $("#data-text").innerHTML = T("data").map((p) => p.startsWith("<ul") ? p : `<p>${p}</p>`).join("");
    const stats = catalog.stats || {};
    const endpoints = Object.values(stats).reduce((s, x) => s + (x.endpoints || 0), 0);
    const updated = new Date(catalog.generated);
    const dateStr = isNaN(updated) ? catalog.generated : updated.toLocaleDateString(state.lang + "-CH", { day: "numeric", month: "short", year: "numeric" });
    $("#kpis").innerHTML = [
      [T("kpiDatasets"), fmt(D.length)], [T("kpiEndpoints"), fmt(endpoints)],
      [T("kpiOwners"), fmt(owners.length)], [T("kpiUpdated"), dateStr]
    ].map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("");
    $("#footer-updated").textContent = T("updated", dateStr);
    renderQuality();
  }

  let qualitySort = { key: "layers", dir: -1 };
  function renderQuality() {
    const stats = catalog.stats || {};
    const rows = owners.filter((o) => stats[o.code]).map((o) => {
      const s = stats[o.code];
      const pct = (k) => s.layers ? Math.round(100 * s[k] / s.layers) : 0;
      return { o, label: ownerLabel(o), endpoints: s.endpoints || 0, layers: s.layers, abstract: pct("abstract"), keywords: pct("keywords"), metadata: pct("metadata"), contact: pct("contact") };
    });
    const { key, dir } = qualitySort;
    rows.sort((a, b) => (key === "label" ? a.label.localeCompare(b.label) : a[key] - b[key]) * dir || a.label.localeCompare(b.label));
    const cols = [["label", T("colOwner")], ["endpoints", T("colEndpoints")], ["layers", T("colLayers")], ["abstract", T("colAbstract")], ["keywords", T("colKeywords")], ["metadata", T("colMetadata")], ["contact", T("colContact")]];
    const bar = (v) => `<div class="pct" title="${v} %"><div class="pct-track"><div class="pct-fill" style="width:${v}%"></div></div><span>${v}%</span></div>`;
    $("#quality-table").innerHTML = `<thead><tr>${cols.map(([k, l]) => `<th scope="col" data-sort="${k}" ${k === key ? `aria-sort="${dir > 0 ? "ascending" : "descending"}"` : ""}>${esc(l)}</th>`).join("")}</tr></thead>
      <tbody>${rows.map((r) => `<tr><td>${esc(r.label)}</td><td class="num">${fmt(r.endpoints)}</td><td class="num">${fmt(r.layers)}</td><td>${bar(r.abstract)}</td><td>${bar(r.keywords)}</td><td>${bar(r.metadata)}</td><td>${bar(r.contact)}</td></tr>`).join("")}</tbody>`;
  }

  function applyI18n() {
    document.documentElement.lang = state.lang;
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = T(el.dataset.i18n); });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = T(el.dataset.i18nPlaceholder); });
    document.querySelectorAll("#lang-switch button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === state.lang)));
    $("#theme-toggle").setAttribute("aria-label", T("theme"));
    $("#map").setAttribute("aria-label", T("mapLabel"));
  }

  // ------------------------------------------------------------ URL state
  function writeHash() {
    const p = new URLSearchParams();
    if (state.q) p.set("q", state.q);
    if (state.region) p.set("r", state.region);
    if (state.owner) p.set("o", state.owner);
    if (state.kinds.size) p.set("k", [...state.kinds].join(","));
    if (state.types.size) p.set("t", [...state.types].join(","));
    if (state.selection.length) p.set("sel", state.selection.map((i) => D[i].id).join("."));
    const h = p.toString();
    history.replaceState(null, "", h ? "#" + h : location.pathname + location.search);
  }

  function readHash() {
    const p = new URLSearchParams(location.hash.slice(1));
    state.q = p.get("q") || "";
    state.region = p.get("r") || "";
    state.owner = p.get("o") || "";
    state.kinds = new Set((p.get("k") || "").split(",").filter(Boolean));
    state.types = new Set((p.get("t") || "").split(",").filter(Boolean));
    const sel = (p.get("sel") || "").split(".").filter(Boolean).map((id) => idIndex.get(id)).filter((i) => i !== undefined);
    return sel;
  }

  // ------------------------------------------------------------- updating
  function update({ keepPage = false } = {}) {
    const shown = state.shown;
    runSearch();
    if (keepPage) state.shown = shown;
    renderResults();
    renderFilters();
    refreshCoverage();
    writeHash();
  }

  let searchTimer = null;
  function onSearchInput(e) {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      state.q = e.target.value.trim();
      state.owner = "";
      update();
    }, 160);
  }

  function bindEvents() {
    $("#q").addEventListener("input", onSearchInput);
    $("#search-form").addEventListener("submit", (e) => { e.preventDefault(); state.q = $("#q").value.trim(); update(); });
    document.addEventListener("keydown", (e) => {
      if (e.key === "/" && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
        e.preventDefault(); $("#q").focus();
      }
      if (e.key === "Escape") document.querySelectorAll("details.more[open]").forEach((d) => d.removeAttribute("open"));
    });
    document.addEventListener("click", (e) => {
      document.querySelectorAll("details.more[open]").forEach((d) => { if (!d.contains(e.target)) d.removeAttribute("open"); });
    });

    $("#topics").addEventListener("click", (e) => {
      const b = e.target.closest("[data-topic]");
      if (!b) return;
      $("#q").value = b.dataset.topic;
      state.q = b.dataset.topic;
      update();
    });
    $("#kind-filter").addEventListener("click", (e) => {
      const b = e.target.closest("[data-kind]");
      if (!b) return;
      const k = b.dataset.kind;
      state.kinds.has(k) ? state.kinds.delete(k) : state.kinds.add(k);
      update();
    });
    $("#type-filter").addEventListener("click", (e) => {
      const b = e.target.closest("[data-type]");
      if (!b) return;
      const t = b.dataset.type;
      state.types.has(t) ? state.types.delete(t) : state.types.add(t);
      update();
    });
    $("#region-filter").addEventListener("change", (e) => { state.region = e.target.value; state.owner = ""; update(); });
    $("#facets").addEventListener("click", (e) => {
      const b = e.target.closest("[data-owner]");
      if (!b) return;
      state.owner = state.owner === b.dataset.owner ? "" : b.dataset.owner;
      update();
    });
    $("#show-more").addEventListener("click", () => {
      state.shown += PAGE_SIZE;
      renderResults();
    });
    $("#export-csv").addEventListener("click", exportCsv);

    $("#results").addEventListener("click", (e) => {
      const card = e.target.closest(".card");
      if (!card) return;
      const i = +card.dataset.i;
      const d = D[i];
      const act = e.target.closest("[data-act]")?.dataset.act;
      if (act === "toggle") isSelected(i) ? removeFromSelection(i) : addToSelection([i]);
      else if (act === "qgis") exportQgis([d]);
      else if (act === "arcgis") exportArcgis([d]);
      else if (act === "copy") copy(e.target.closest("[data-act]").dataset.url);
      else if (act === "expand") {
        const p = card.querySelector(".abstract");
        const clamped = p.classList.toggle("clamped");
        e.target.textContent = clamped ? T("more") : T("less");
      }
    });
    $("#results").addEventListener("mouseover", (e) => {
      const card = e.target.closest(".card");
      if (card && map) highlightBbox(D[+card.dataset.i]);
    });
    $("#results").addEventListener("mouseleave", () => highlightBbox(null));

    $("#selection-list").addEventListener("click", (e) => {
      const item = e.target.closest(".sel-item");
      if (!item) return;
      const i = +item.dataset.i;
      const act = e.target.closest("[data-act]")?.dataset.act;
      if (act === "remove") removeFromSelection(i);
      else if (act === "zoom") zoomToDatasets([D[i]]);
      else if (act === "legend") { const ls = state.layerState.get(i); ls.legend = !ls.legend; renderSelection(); }
    });
    $("#selection-list").addEventListener("change", (e) => {
      const item = e.target.closest(".sel-item");
      if (!item || e.target.dataset.act !== "vis") return;
      const i = +item.dataset.i;
      state.layerState.get(i).visible = e.target.checked;
      syncMapLayers(); updateExports();
    });
    $("#selection-list").addEventListener("input", (e) => {
      const item = e.target.closest(".sel-item");
      if (!item || e.target.dataset.act !== "opacity") return;
      const i = +item.dataset.i;
      state.layerState.get(i).opacity = +e.target.value;
      syncMapLayers(); updateExports();
    });
    $("#selection-list").addEventListener("mouseover", (e) => {
      const item = e.target.closest(".sel-item");
      if (item && map) highlightBbox(D[+item.dataset.i]);
    });
    $("#selection-list").addEventListener("mouseleave", () => highlightBbox(null));
    $("#clear-selection").addEventListener("click", () => {
      state.selection = []; state.layerState.clear();
      setCoverageMode("results");
      selectionChanged();
    });
    $("#dl-qgis").addEventListener("click", () => exportQgis(state.selection.map((i) => D[i])));
    $("#dl-arcgis").addEventListener("click", () => exportArcgis(state.selection.map((i) => D[i])));
    $("#share-link").addEventListener("click", () => { writeHash(); copy(location.href).then(() => toast(T("linkCopied"))); });

    $("#coverage-mode").addEventListener("click", (e) => {
      const b = e.target.closest("[data-mode]");
      if (b) setCoverageMode(b.dataset.mode);
    });
    $("#basemap").addEventListener("change", (e) => setBasemap(e.target.value));

    $("#lang-switch").addEventListener("click", (e) => {
      const b = e.target.closest("[data-lang]");
      if (!b) return;
      state.lang = b.dataset.lang;
      store.set("lang", state.lang);
      applyI18n(); renderFilters(); renderResults(); renderSelection(); renderLegend(); renderInfo();
    });
    $("#theme-toggle").addEventListener("click", () => {
      const root = document.documentElement;
      const dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
      root.dataset.theme = dark ? "light" : "dark";
      store.set("theme", root.dataset.theme);
    });
    $("#quality-table").addEventListener("click", (e) => {
      const th = e.target.closest("th[data-sort]");
      if (!th) return;
      const k = th.dataset.sort;
      qualitySort = { key: k, dir: qualitySort.key === k ? -qualitySort.dir : (k === "label" ? 1 : -1) };
      renderQuality();
    });
    $("#mobile-tabs").addEventListener("click", (e) => {
      const b = e.target.closest("[data-tab]");
      if (!b) return;
      document.body.dataset.tab = b.dataset.tab;
      document.querySelectorAll("#mobile-tabs button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
      if (b.dataset.tab === "map") setTimeout(onMapShown, 30);
    });
    window.addEventListener("hashchange", () => {
      const sel = readHash();
      $("#q").value = state.q;
      if (sel.length) { state.selection = []; state.layerState.clear(); addToSelection(sel, { fit: true }); }
      update();
    });
  }

  // ------------------------------------------------------------------ init
  function initPrefs() {
    const theme = store.get("theme");
    if (theme === "dark" || theme === "light") document.documentElement.dataset.theme = theme;
    const saved = store.get("lang");
    const nav = (navigator.language || "de").slice(0, 2);
    state.lang = I18N[saved] ? saved : I18N[nav] ? nav : "de";
    const bm = store.get("basemap");
    if (["grau", "farbe", "luftbild", "none"].includes(bm)) state.basemap = bm;
    document.body.dataset.tab = "list";
  }

  async function init() {
    initPrefs();
    applyI18n();
    $("#results").innerHTML = '<li class="skeleton"></li><li class="skeleton"></li><li class="skeleton"></li>';
    $("#results-count").textContent = T("loading");
    try {
      const [cat, geo] = await Promise.all([
        fetch(CATALOG_URL).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }),
        fetch(BOUNDARIES_URL).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
      ]);
      catalog = cat;
      regionsGeo = geo;
    } catch (e) {
      $("#results").innerHTML = "";
      $("#results-count").textContent = T("loadError");
      console.error(e);
      return;
    }
    buildModel();
    const sel = readHash();
    $("#q").value = state.q;
    renderFilters();
    try { initMap(); } catch (e) { console.error("Map init failed", e); }
    bindEvents();
    setCoverageMode("results");
    renderInfo();
    update();
    renderSelection();
    if (sel.length) addToSelection(sel, { fit: true });
  }

  // Small scripting API (handy for testing and power users)
  window.GeoHarvester = {
    datasets: () => D,
    selection: () => state.selection.map((i) => D[i]),
    search: (q) => { state.q = q; $("#q").value = q; update(); return state.results; },
    mapGeoUrl: (list) => mapGeoUrl(list || state.selection.map((i) => D[i])).url,
    qlr: (list) => buildQlr(list || state.selection.map((i) => D[i]), "GeoHarvester"),
    lyrx: (list) => buildLyrx(list || state.selection.map((i) => D[i]))
  };

  init();
})();
