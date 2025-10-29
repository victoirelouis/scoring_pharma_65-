# scoring_pharma_65-
Scoring du potentiel de ventes des pharmacies pour les 65+

# MÉTHODOLOGIE DÉTAILLÉE : CALCUL DU POTENTIEL 65+ DES PHARMACIES

**Version** : 4.1  
**Date** : 24 octobre 2025  
**Projet** : Modélisation Potentiel Pharmacies 65+

---

## INTRODUCTION ET OBJECTIFS

Ce projet vise à modéliser de manière précise et exhaustive le potentiel commercial des pharmacies françaises auprès de la population âgée de 65 ans et plus. L'objectif principal est de calculer, pour chacune des 20 000 pharmacies de France, le nombre de clients seniors potentiels qu'elle peut capter, ainsi que le chiffre d'affaires théorique associé, décomposé entre produits de prescription (Rx) et parapharmacie. Cette modélisation s'appuie sur une approche géographique fine, utilisant le maillage territorial des zones IRIS de l'INSEE, soit environ 50 000 zones couvrant l'ensemble du territoire français.

Le projet va au-delà d'une simple estimation globale en proposant une segmentation détaillée de la population cible. Celle-ci est découpée en trois tranches d'âge (65-74 ans, 75-84 ans, et 85 ans et plus) et distinguée par genre (femmes et hommes). Cette granularité permet de mieux appréhender les comportements de consommation différenciés selon l'âge et le sexe, puisque les besoins pharmaceutiques et parapharmaceutiques évoluent significativement avec le vieillissement et présentent des spécificités selon le genre.

La temporalité du modèle est annuelle, avec toutefois la prise en compte de modulations mensuelles pour intégrer les effets de saisonnalité, particulièrement importants dans les zones touristiques où l'afflux de population peut être massif durant certaines périodes de l'année. Cette dimension saisonnière est essentielle pour éviter de sous-estimer le potentiel de pharmacies situées dans des zones balnéaires, montagnardes ou thermales.

---

## PRINCIPE GÉNÉRAL DE LA MÉTHODE

La méthodologie repose sur un modèle gravitaire structuré en trois phases successives et complémentaires. Ce type de modèle, largement utilisé en géomarketing et en économie spatiale, permet de simuler les flux de clientèle entre des lieux de résidence (les zones IRIS) et des points de vente (les pharmacies) en fonction de leur attractivité respective et de la distance qui les sépare.

La première phase consiste à calculer un score d'attractivité pour chaque couple formé par une pharmacie et une zone IRIS environnante. Ce score, compris entre 0 et 5, mesure le pouvoir d'attraction de la pharmacie pour les résidents seniors de cette zone. Il intègre de multiples dimensions : la taille de la pharmacie, son environnement médical et socio-économique, la présence de pôles d'attraction à proximité (comme des établissements de santé, des transports en commun ou des commerces), la mobilité spécifique des personnes âgées, et bien sûr la distance réelle qui sépare la zone de la pharmacie.

La deuxième phase utilise le modèle de Huff, un modèle probabiliste qui permet de répartir la population d'une zone donnée entre les différentes pharmacies concurrentes situées à proximité. Pour chaque zone IRIS, on identifie toutes les pharmacies accessibles dans un rayon défini, puis on calcule la part de marché de chaque pharmacie en fonction de son attractivité relative par rapport aux autres. La population de la zone est ensuite allouée proportionnellement à ces parts de marché, avec une pondération supplémentaire tenant compte du degré de couverture géographique de la zone par l'isochrone de chaque pharmacie. Cette approche garantit une allocation réaliste de la population, évitant les double-comptages et respectant les principes de concurrence spatiale.

La troisième et dernière phase convertit la population captée en chiffre d'affaires théorique. Pour cela, on applique des paniers moyens annuels différenciés par tranche d'âge et par type de produit (Rx ou parapharmacie), puis on module ces montants avec des coefficients régionaux reflétant les spécificités territoriales de consommation pharmaceutique. Cette phase permet d'obtenir une projection financière cohérente avec les réalités économiques observées sur le terrain.

---

## PHASE 1 : CALCUL DE L'ATTRACTIVITÉ DES PHARMACIES

### Vue d'ensemble de l'attractivité

L'attractivité d'une pharmacie pour les seniors d'une zone donnée est modélisée par une formule composite qui combine plusieurs facteurs multiplicatifs pondérés par un facteur de distance. Cette formule s'écrit de manière générale comme suit : l'attractivité est égale au produit de quatre composantes (la taille de la pharmacie, les facteurs locaux, l'impact des hubs de proximité et la mobilité des seniors), le tout divisé par la distance élevée à une puissance beta qui représente la sensibilité à l'éloignement.

Mathématiquement, on exprime cela par : Attractivité = (S × F × (1 + H) × M) / Distance^β. Chacune de ces composantes a été soigneusement calibrée pour refléter les déterminants réels de l'attractivité des pharmacies auprès des personnes âgées, en s'appuyant sur des données empiriques, des avis d'experts et des observations terrain.

### Composante S : Taille de la pharmacie

La taille de la pharmacie est approximée par son chiffre d'affaires annuel, qui constitue un indicateur indirect mais fiable de sa capacité d'accueil, de la diversité de son offre et de sa notoriété locale. Pour éviter que les très grandes pharmacies n'écrasent complètement les plus petites dans les calculs, on applique une transformation logarithmique qui compresse l'échelle des valeurs. Concrètement, on calcule le logarithme du ratio entre le chiffre d'affaires de la pharmacie et un CA de référence fixé à 500 000 euros, qui correspond approximativement au CA médian des pharmacies françaises.

Cette transformation produit un score centré autour de zéro pour les pharmacies moyennes. Pour les très petites pharmacies, le score pourrait devenir fortement négatif, et pour les très grandes, très positif. Afin d'éviter des valeurs extrêmes qui déséquilibreraient le modèle, on applique des bornes : le score S est limité à un minimum de -0.5 et un maximum de 1.0. Ainsi, une pharmacie dont le CA est deux fois supérieur à la référence aura un score S positif qui augmentera son attractivité, tandis qu'une pharmacie très petite restera pénalisée mais de manière maîtrisée.

### Composante F : Facteurs locaux

Les facteurs locaux regroupent quatre dimensions essentielles qui caractérisent l'environnement de la pharmacie et sa capacité à attirer et servir une clientèle senior. Ces quatre dimensions sont la densité de professionnels de santé, le niveau socio-économique de la zone, le mix du chiffre d'affaires de la pharmacie, et la densité de population âgée dans les environs. Chaque dimension reçoit un poids spécifique reflétant son importance relative, puis les quatre scores sont agrégés en une moyenne pondérée.

La densité médicale est le facteur le plus important, avec un poids de 30 %. Elle mesure le nombre de médecins, en particulier les spécialistes pertinents pour les seniors comme les cardiologues et les rhumatologues, présents dans un rayon de proximité autour de la pharmacie. Les données proviennent du répertoire RPPS et sont enrichies par des requêtes sur OpenStreetMap. Pour tenir compte de la spécificité des pathologies seniors, les cardiologues reçoivent une pondération de 1.5 et les rhumatologues de 1.3 par rapport aux généralistes. On calcule ensuite un ratio entre la densité observée et une densité cible de 2.5 médecins pour 1000 habitants, valeur considérée comme représentant un maillage médical satisfaisant en France. Ce ratio est plafonné pour éviter que des zones exceptionnellement bien dotées ne faussent les résultats.

Le niveau socio-économique, qui représente 20 % du poids, est évalué via le revenu médian annuel de la zone IRIS par rapport à un revenu médian national de référence de 22 000 euros. Ce facteur capture l'idée que les zones plus aisées présentent généralement une consommation parapharmaceutique et de produits de confort supérieure, ce qui peut renforcer l'attractivité de pharmacies proposant une offre élargie.

Le mix de chiffre d'affaires, pesant 25 %, mesure la part du CA de la pharmacie qui provient de produits et services particulièrement pertinents pour les seniors. Ce ratio est calculé comme suit : (CA éthique + Delta) / CA total, où le CA éthique représente les médicaments prescrits et le delta représente les dispositifs médicaux hors prescription (capteurs de glycémie, tensiomètres, bas de contention, orthopédie, maintien à domicile). En effet, ces deux composantes reflètent une pharmacie orientée santé et besoins spécifiques des personnes âgées, par opposition au CA conseil qui inclut une large part de cosmétiques et produits d'hygiène courante moins pertinents pour cette population. Une pharmacie dont 70 % du CA provient de l'éthique et des dispositifs médicaux sera considérée comme plus attractive pour les personnes âgées qu'une pharmacie généraliste dont seulement 50 % du CA provient de ces segments.

Enfin, la densité de population 65+, également à 25 %, évalue la concentration de personnes âgées dans les zones IRIS entourant la pharmacie. Une forte densité senior crée un effet d'écosystème : la pharmacie s'adapte naturellement à cette clientèle, propose des services dédiés, et bénéficie d'un bouche-à-oreille favorable. On calcule cette densité dans un rayon euclidien de 2 km autour de la pharmacie et on la normalise par rapport à une densité nationale médiane. L'utilisation de la distance euclidienne plutôt que des isochrones pour ce calcul spécifique se justifie par le fait qu'il s'agit ici de mesurer un effet d'environnement et d'écosystème global plutôt qu'une accessibilité directe : ce qui compte est la présence d'une concentration de seniors dans le voisinage large de la pharmacie, indépendamment de leur capacité à s'y rendre physiquement. Cette densité environnante influence l'offre de la pharmacie, son aménagement, et sa réputation locale, même pour des seniors qui ne sont pas directement dans sa zone de chalandise accessible.

### Composante H : Impact des hubs de proximité

Les hubs désignent des points d'intérêt qui génèrent des flux de passage ou qui sont des destinations habituelles pour les seniors. Leur présence à proximité immédiate d'une pharmacie augmente ses opportunités de contact avec sa clientèle cible. On distingue quatre grandes catégories de hubs : les établissements de santé et médico-sociaux, les pôles de transport en commun, les commerces et marchés, et les lieux de loisirs ou de culture.

Chaque type de hub génère un bonus d'attractivité, mais ce bonus est plafonné par catégorie et globalement pour éviter les surestimations. Par exemple, la présence d'un EHPAD à moins de 300 mètres apporte un bonus de 25 %, car elle génère des visites régulières de résidents accompagnés, de familles, et de personnels soignants. Un marché hebdomadaire à proximité ajoute 20 %, car il constitue un rituel social majeur pour les seniors qui combinent souvent leurs achats alimentaires avec un passage à la pharmacie. Un arrêt de bus accessible apporte 15 %, reflétant l'importance des transports en commun pour les personnes âgées qui ne conduisent plus. En revanche, une station de métro n'apporte que 8 %, car les escaliers et la profondeur des stations constituent souvent un obstacle pour cette population.

Les données sur ces hubs proviennent de sources variées : FINESS pour les établissements de santé, OpenStreetMap pour les commerces et les transports, APIs de transport public pour les arrêts de bus et métro. Chaque catégorie de hub ne peut contribuer qu'à hauteur de 25 % maximum, et l'impact cumulé de tous les hubs est plafonné à 50 %, ce qui signifie que même une pharmacie idéalement située ne verra jamais son attractivité multipliée par plus de 1.5 via cet effet.

### Composante M : Mobilité des seniors

La mobilité des personnes âgées décroît fortement avec l'âge, et cette réalité doit être intégrée dans le modèle. On applique donc des facteurs de mobilité différenciés selon la tranche d'âge considérée. Les 65-74 ans, généralement encore autonomes et souvent conducteurs, reçoivent un facteur de 1.0, qui ne modifie pas l'attractivité. Les 75-84 ans, dont une partie significative commence à réduire ses déplacements et à dépendre davantage de tiers ou de transports en commun, reçoivent un facteur de 0.7, ce qui réduit mécaniquement l'attractivité de pharmacies éloignées. Enfin, les 85 ans et plus, souvent très limités dans leurs déplacements, reçoivent un facteur de 0.5, reflétant leur dépendance accrue et leur tendance à fréquenter quasi exclusivement les pharmacies de très grande proximité.

Ces coefficients proviennent d'études de mobilité de l'INSEE et sont cohérents avec les observations de terrain montrant que les seniors les plus âgés privilégient massivement la proximité immédiate, quitte à renoncer à des pharmacies potentiellement mieux dotées mais plus éloignées.

### Composante Distance et coefficient beta

La distance joue un rôle central dans tout modèle gravitaire. Ici, on utilise non pas la distance euclidienne à vol d'oiseau, mais la distance-temps réelle calculée via des isochrones. Les isochrones sont des polygones représentant l'ensemble des points accessibles depuis la pharmacie en un temps donné (par exemple 10 minutes à pied ou en voiture). Ces isochrones sont calculées à l'aide de la bibliothèque OSMnx qui exploite les données du réseau routier et piétonnier d'OpenStreetMap. Cette approche permet de capturer les obstacles réels : rivières sans pont, autoroutes infranchissables, sens uniques, pentes difficiles pour les seniors, etc.

Le coefficient beta détermine la sensibilité à la distance : plus beta est élevé, plus la distance a un effet pénalisant fort. Ce coefficient varie selon le type de zone géographique. En zone urbaine dense, où les alternatives sont nombreuses et proches, beta est fixé à 1.6, ce qui signifie que les seniors sont moins tolérants aux distances car ils ont le choix. En zone urbaine classique, beta monte à 1.8. En périurbain, il atteint 2.0, et en zone rurale, où la distance est une contrainte majeure, il culmine à 2.2. De plus, pour les 85 ans et plus, on ajoute systématiquement 0.30 à beta, car cette population est particulièrement sensible à l'éloignement.

Ainsi, une distance de 10 minutes en zone urbaine dense divisera l'attractivité par environ 25, alors qu'en zone rurale, elle la divisera par 48, et pour les 85+, cet effet sera encore plus marqué. Ce mécanisme garantit que le modèle respecte les comportements observés où les seniors ruraux, malgré des distances plus grandes, sont contraints d'accepter des déplacements plus longs, mais restent très sensibles à toute augmentation de cette distance.

### Modulation par la saisonnalité

Certaines pharmacies connaissent des variations importantes de leur clientèle selon la période de l'année, notamment dans les zones touristiques. Pour tenir compte de ce phénomène, on applique des facteurs multiplicateurs saisonniers qui augmentent artificiellement l'attractivité durant les mois de forte affluence.

La classification d'une pharmacie selon son type de zone touristique repose sur un ensemble de critères géographiques et statistiques. Pour identifier les zones balnéaires, on utilise plusieurs indicateurs : la proximité du littoral (distance à la côte inférieure à 5 km), la présence de plages référencées dans les bases de données géographiques, et surtout le taux de résidences secondaires dans les communes environnantes (généralement supérieur à 40 % pour les zones balnéaires typiques). Les données de l'INSEE sur les résidences secondaires et les logements vacants sont croisées avec des données de fréquentation touristique estivale lorsque celles-ci sont disponibles via les observatoires régionaux du tourisme.

Les zones de montagne sont identifiées par l'altitude (généralement au-dessus de 800 mètres), la présence de stations de ski référencées dans des bases nationales comme celle de Domaine Skiable de France, et le nombre de remontées mécaniques dans un rayon de 10 km. On distingue les zones de montagne à forte activité hivernale (ski alpin) de celles à activité estivale (randonnée, thermalisme d'altitude). Le croisement avec les données de l'INSEE sur les résidences secondaires permet de confirmer le caractère touristique de ces zones.

Les zones thermales sont identifiées via le fichier FINESS qui répertorie les établissements thermaux agréés, ainsi que par des listes officielles des communes thermales françaises. Ces zones ont la particularité d'avoir une saisonnalité spécifique, généralement concentrée au printemps et à l'automne, périodes traditionnelles des cures thermales. On recense environ 90 communes thermales en France.

Une fois le type de zone identifié, les facteurs saisonniers sont appliqués de manière mensuelle. Les pharmacies situées en zone balnéaire voient leur attractivité multipliée par 1.9 durant les mois de juin, juillet, août et septembre, reflétant l'afflux massif de touristes et de résidents secondaires, dont une proportion importante est senior. Les pharmacies de montagne bénéficient d'un facteur de 1.8 durant les mois de décembre, janvier, février et mars pour la saison de ski. Les pharmacies situées dans des villes thermales appliquent un facteur de 1.25 durant les mois d'avril, mai, septembre et octobre, correspondant aux saisons de cure. Ces coefficients sont issus de données métier et d'observations historiques de l'évolution du chiffre d'affaires de ces pharmacies.

Il est important de noter que ces facteurs ne s'appliquent qu'aux mois concernés et uniquement aux pharmacies identifiées dans les types de zones correspondantes. Une pharmacie classée en zone standard ne bénéficiera d'aucune modulation saisonnière.

---

## PHASE 2 : MODÈLE DE HUFF ET RÉPARTITION DE LA POPULATION

### Principe du modèle de Huff

Le modèle de Huff est un modèle probabiliste développé dans les années 1960 pour prédire les parts de marché de points de vente concurrents. Son principe repose sur l'idée que la probabilité qu'un consommateur choisisse un commerce particulier est proportionnelle à l'attractivité de ce commerce et inversement proportionnelle à la somme des attractivités de tous les commerces concurrents accessibles.

Dans notre contexte, pour chaque zone IRIS, on identifie d'abord toutes les pharmacies dont la zone de chalandise (définie par les isochrones) intersecte avec cette zone IRIS. Ces pharmacies constituent l'ensemble concurrentiel pour cette zone. On calcule ensuite la part de marché de chaque pharmacie en divisant son score d'attractivité par la somme des attractivités de toutes les pharmacies concurrentes. Cette part de marché représente la probabilité théorique qu'un senior de cette zone fréquente cette pharmacie plutôt qu'une autre.

Mathématiquement, la part de marché de la pharmacie j pour la zone i s'écrit : Part_j = Attractivité_j / Σ(Attractivité_k) où la somme porte sur toutes les pharmacies k dont la zone de chalandise couvre la zone i. Par construction, la somme de toutes les parts de marché pour une zone donnée est égale à 1, ce qui garantit la cohérence du modèle.

### Pondération par la couverture géométrique des IRIS

Un raffinement important du modèle consiste à pondérer la population accessible par le degré de couverture géographique de la zone IRIS par l'isochrone de la pharmacie. En effet, une isochrone ne couvre pas toujours l'intégralité d'une zone IRIS : elle peut n'en couvrir qu'une fraction, par exemple 30 % de la surface si la pharmacie est en bordure de zone ou si des obstacles naturels limitent l'accès.

Pour chaque couple (pharmacie, zone IRIS), on calcule le ratio de couverture en intersectant géométriquement le polygone de l'isochrone avec le polygone de la zone IRIS, puis en divisant l'aire de l'intersection par l'aire totale de l'IRIS. Ce ratio, compris entre 0 et 1, représente la proportion de la population de la zone qui est géographiquement accessible à la pharmacie. On multiplie ensuite la population totale 65+ de l'IRIS par ce ratio pour obtenir la population accessible.

Cette approche permet d'éviter les biais de double-comptage et de mieux respecter la réalité des bassins de vie. Une zone IRIS située à cheval entre deux pharmacies verra sa population correctement répartie entre les deux en fonction à la fois de l'attractivité de chaque pharmacie et de la surface effectivement couverte par chacune.

### Allocation de la population captée

Une fois les parts de marché et les populations accessibles calculées, on procède à l'allocation finale. Pour chaque couple (pharmacie, zone), la population captée est égale au produit de la population accessible et de la part de marché. Concrètement, si une zone IRIS compte 1 000 seniors, qu'une pharmacie couvre 50 % de sa surface (ratio de couverture = 0.5), et que cette pharmacie détient 40 % de part de marché parmi les concurrents de cette zone, alors cette pharmacie captera 1000 × 0.5 × 0.4 = 200 seniors de cette zone.

On répète ce calcul pour toutes les zones IRIS de la zone de chalandise de la pharmacie, puis on agrège les résultats pour obtenir la population totale captée par la pharmacie. Cette agrégation est réalisée en conservant la segmentation par âge et par genre, ce qui permet de dresser un profil détaillé de la clientèle senior de chaque pharmacie.

Un contrôle qualité essentiel à cette étape consiste à vérifier que la somme des populations captées par toutes les pharmacies pour une zone donnée ne dépasse pas la population réelle de cette zone, et idéalement s'en approche. Un taux de conservation de population supérieur à 95 % est considéré comme acceptable, un taux inférieur peut signaler des zones mal couvertes ou des erreurs de calcul.

### Gestion des zones sans concurrence

Dans certaines zones rurales très isolées, il peut arriver qu'une seule pharmacie couvre une zone IRIS donnée. Dans ce cas, le modèle de Huff attribue mécaniquement une part de marché de 100 % à cette pharmacie pour cette zone, ce qui est logique et cohérent. Cependant, si aucune pharmacie ne couvre une zone (ce qui peut arriver pour des zones très reculées ou inhabitées), la population de cette zone n'est captée par personne, ce qui peut générer un warning de conservation de population. Ces situations doivent être identifiées et analysées pour s'assurer qu'elles correspondent bien à des réalités géographiques et non à des erreurs de données.

---

## TRAITEMENT DES ISOCHRONES ET CALCUL DES DISTANCES

### Génération des isochrones

Les isochrones sont générées en amont de la phase de calcul principal, car leur création est coûteuse en temps de calcul. On utilise la bibliothèque OSMnx qui permet de télécharger les graphes routiers et piétonniers depuis OpenStreetMap, puis d'appliquer des algorithmes de plus court chemin pour déterminer quels points sont accessibles en un temps donné depuis la pharmacie.

Pour chaque pharmacie, on génère plusieurs isochrones correspondant à différents temps de trajet : typiquement 5, 10, 15 et 20 minutes à pied, et 5, 10, 15 minutes en voiture. Le choix du mode de transport dépend du type de zone : en zone urbaine dense, on privilégie les isochrones piétonnes, tandis qu'en zone rurale, ce sont les isochrones en voiture qui sont pertinentes. Dans certains cas, on peut combiner les deux modes pour couvrir différents profils de mobilité.

Les isochrones sont stockées sous forme de polygones géographiques dans un format standard (GeoJSON ou Shapefile), ce qui permet ensuite de les croiser avec les contours des zones IRIS. Ce croisement géométrique est réalisé avec des bibliothèques comme GeoPandas qui offrent des fonctions optimisées d'intersection, d'union et de calcul de surfaces.

### Gestion du cache et optimisation

Étant donné le nombre important de pharmacies (20 000) et de zones IRIS (50 000), le calcul exhaustif de toutes les intersections possibles serait prohibitif. On met donc en place un système de cache qui stocke les résultats des intersections déjà calculées. Avant de calculer une intersection, on vérifie si elle est présente dans le cache. Si oui, on récupère directement le ratio de couverture. Si non, on effectue le calcul et on enregistre le résultat dans le cache pour une utilisation ultérieure.

Ce cache est sauvegardé sous forme de fichier pickle Python, ce qui permet de le réutiliser d'une exécution à l'autre. Lors des mises à jour du modèle, si les isochrones n'ont pas changé, on peut directement réutiliser le cache sans recalculer les intersections, ce qui réduit considérablement les temps de traitement.

De plus, on applique des filtres préalables pour éviter de calculer des intersections manifestement nulles. Par exemple, si la distance à vol d'oiseau entre une pharmacie et le centroïde d'une zone IRIS est supérieure à 30 km, on peut raisonnablement supposer que l'isochrone de cette pharmacie ne couvrira pas cette zone, et on évite le calcul coûteux de l'intersection géométrique.

### Limites et hypothèses

Le modèle repose sur plusieurs hypothèses qui constituent aussi ses limites. Tout d'abord, on suppose que les données d'OpenStreetMap sont complètes et à jour, ce qui n'est pas toujours le cas, particulièrement dans les zones rurales où certains chemins peuvent ne pas être cartographiés. Ensuite, les isochrones sont calculées pour un instant donné et ne prennent pas en compte les variations de trafic au cours de la journée. Une pharmacie accessible en 10 minutes le matin peut être à 25 minutes aux heures de pointe.

On suppose également que tous les seniors ont accès aux modes de transport considérés, ce qui n'est pas toujours vrai : certains ne conduisent plus et n'ont pas accès aux transports en commun. Le facteur de mobilité M tente de corriger cela, mais de manière imparfaite. Enfin, le modèle ne prend pas en compte les préférences individuelles irrationnelles ou les habitudes ancrées : un senior peut continuer de fréquenter une pharmacie éloignée par fidélité ou par habitude, même si une pharmacie plus proche et plus attractive existe.

---

## PHASE 3 : PROJECTION DU CHIFFRE D'AFFAIRES 65+

### Principe de la projection

Une fois la population captée calculée pour chaque pharmacie, avec sa décomposition par âge et par genre, on procède à la conversion de cette population en chiffre d'affaires théorique. Cette conversion repose sur l'application de paniers moyens annuels qui représentent la dépense moyenne d'un senior dans une pharmacie au cours d'une année, séparément pour les produits de prescription (Rx) et pour la parapharmacie.

Ces paniers moyens sont calibrés à partir de données de la Caisse Nationale d'Assurance Maladie pour le Rx, et d'études de marché pour la parapharmacie. Ils varient selon la tranche d'âge, car les besoins évoluent fortement avec le vieillissement. Les 65-74 ans, souvent en meilleure santé relative, ont des dépenses Rx modérées mais des dépenses parapharmacie encore soutenues (produits de prévention, cosmétiques, compléments alimentaires). Les 75-84 ans voient leurs dépenses Rx augmenter fortement avec l'apparition de pathologies chroniques, tandis que leurs dépenses parapharmacie commencent à diminuer. Enfin, les 85 ans et plus présentent les dépenses Rx les plus élevées (polypathologies, traitements lourds) mais les dépenses parapharmacie les plus faibles, se limitant à l'essentiel.

### Paniers moyens par âge et par produit

Les paniers moyens utilisés dans le modèle sont les suivants. Pour la tranche 65-74 ans, le panier Rx est de 850 euros par an et le panier parapharmacie de 180 euros par an. Pour la tranche 75-84 ans, le panier Rx monte à 1 200 euros par an et le panier parapharmacie descend à 140 euros par an. Pour les 85 ans et plus, le panier Rx culmine à 1 500 euros par an tandis que le panier parapharmacie n'est plus que de 100 euros par an.

Il est important de préciser que le terme "panier Rx" dans le modèle correspond à l'ensemble des dépenses liées à la santé prescrite et aux dispositifs médicaux, soit la somme du CA éthique et du delta dans la nomenclature des données d'entrée. Le terme "panier parapharmacie" correspond au CA conseil. Cette distinction est essentielle car elle reflète le fait que les seniors dépensent majoritairement dans les médicaments prescrits et les dispositifs médicaux de santé, tandis que leur consommation de produits conseil (cosmétiques, hygiène, compléments non prescrits) reste plus modeste et décroît avec l'âge.

Ces valeurs sont des moyennes nationales et servent de base de calcul. On leur applique ensuite des ajustements pour tenir compte des différences de genre. Les hommes présentent en moyenne des dépenses Rx supérieures de 10 % aux femmes, principalement en raison d'une plus forte prévalence de pathologies cardiovasculaires. À l'inverse, les femmes dépensent 15 % de plus en parapharmacie que les hommes, notamment pour les produits cosmétiques et de soin de la peau.

Ainsi, pour calculer le CA Rx d'une pharmacie, on multiplie le nombre de seniors captés dans chaque tranche d'âge par le panier Rx correspondant, en appliquant le coefficient homme ou femme selon le cas, puis on somme sur toutes les tranches. De même pour le CA parapharmacie. Le CA total 65+ est la somme du CA Rx et du CA parapharmacie.

### Coefficients régionaux et typologie des pharmacies

Le modèle ne s'arrête pas à ces moyennes nationales, car il existe des disparités régionales importantes dans les comportements de consommation pharmaceutique. Certaines régions, notamment les zones urbaines aisées et les zones côtières touristiques, présentent une part de parapharmacie supérieure à la moyenne nationale, tandis que les zones rurales vieillissantes ou les zones thermales ont une part de Rx plus élevée.

Pour capturer ces effets, on classe chaque pharmacie dans l'un des cinq types régionaux suivants : urbain aisé, côtier touristique, rural vieillissant, thermal, ou standard. Cette classification s'appuie sur un algorithme de scoring combinant plusieurs critères géographiques, démographiques et socio-économiques.

Le type "urbain aisé" est attribué aux pharmacies situées dans des communes de plus de 50 000 habitants ou dans des agglomérations de plus de 200 000 habitants, dont le revenu médian par unité de consommation est supérieur à 24 000 euros annuels (soit environ 110 % du revenu médian national). On utilise les données INSEE sur les revenus disponibles par commune ainsi que la délimitation des unités urbaines. Ce type caractérise les centres-villes aisés, les beaux quartiers et certaines banlieues huppées.

Le type "côtier touristique" est attribué aux pharmacies situées à moins de 5 km du littoral maritime dans des communes où le taux de résidences secondaires dépasse 30 % et où la population estivale double au minimum par rapport à la population résidente permanente. Les données proviennent de l'INSEE (fichier des logements) et des observatoires régionaux du tourisme. On exclut de cette catégorie les grandes métropoles portuaires qui relèvent plutôt du type urbain aisé.

Le type "rural vieillissant" concerne les pharmacies situées dans des communes de moins de 5 000 habitants avec une densité de population inférieure à 50 habitants par km², un âge médian de la population supérieur à 47 ans, et une part de population de 65 ans et plus supérieure à 25 %. Ces critères permettent d'identifier les zones rurales profondes marquées par le vieillissement démographique et l'exode des jeunes actifs. Les données démographiques proviennent des recensements INSEE.

Le type "thermal" est attribué aux pharmacies situées dans les 90 communes thermales officiellement reconnues et disposant d'établissements thermaux agréés référencés dans le fichier FINESS. Cette catégorie est très spécifique et facilement identifiable via les listes officielles du Conseil National des Établissements Thermaux.

Enfin, le type "standard" est attribué par défaut à toutes les pharmacies qui ne correspondent à aucun des quatre types précédents. Il représente la situation moyenne du territoire français : zones périurbaines, villes moyennes, bourgs ruraux dynamiques, banlieues standard.

Chaque type régional se voit attribuer un ratio Rx et un ratio Para qui représentent la part moyenne du CA d'une pharmacie provenant respectivement des produits de prescription et de la parapharmacie pour les seniors. Ces ratios servent de pondérateurs pour ajuster les paniers moyens à la réalité locale.

Le tableau ci-dessous présente les ratios par type régional :

| Type régional | Ratio Rx 65+ | Ratio Para 65+ | Commentaire |
|---------------|--------------|----------------|-------------|
| Urbain aisé | 48 % | 19 % | Forte consommation para haut de gamme |
| Côtier touristique | 47 % | 20 % | Clientèle touristique aisée en été |
| Rural vieillissant | 54 % | 13 % | Population âgée, peu de para |
| Thermal | 52 % | 15 % | Clientèle curistes, focus santé |
| Standard | 50 % | 16 % | Référence moyenne nationale |

Ces ratios sont appliqués de manière proportionnelle. Par exemple, une pharmacie classée en rural vieillissant verra ses CA Rx et Para multipliés respectivement par 54/50 = 1.08 et 13/16 = 0.81 par rapport à la projection standard. Cela permet de mieux coller aux réalités observées sur le terrain.

### Décomposition par profil et validation

Le modèle produit non seulement un CA total 65+, mais aussi une décomposition complète par tranche d'âge et par genre. Cela permet de dresser le portrait de la clientèle senior de chaque pharmacie : combien de femmes de 75-84 ans, combien d'hommes de 85+, etc. Cette granularité est précieuse pour des actions marketing ciblées ou pour anticiper les besoins en produits spécifiques.

Un dernier ajustement optionnel peut être appliqué pour tenir compte de la conservation du chiffre d'affaires global. Si, en agrégeant toutes les pharmacies, le CA total 65+ projeté s'écarte significativement du CA 65+ observé au niveau national (disponible via des données CNAM ou des organismes professionnels), on peut appliquer un facteur de normalisation global pour recaler les projections. Toutefois, cette opération doit être effectuée avec précaution pour ne pas écraser les variations locales légitimes.

---

## DONNÉES D'ENTRÉE REQUISES

### Données sur les pharmacies

Le modèle nécessite pour chaque pharmacie un ensemble précis et complet d'informations structurées. Voici la liste exhaustive des données requises :

**Identification et localisation :**
- Identifiant unique de la pharmacie (code interne, numéro FINESS ou identifiant RPPS de l'établissement)
- Latitude en degrés décimaux (système WGS84)
- Longitude en degrés décimaux (système WGS84)
- Adresse postale complète (rue, code postal, commune, département)
- Code postal (5 chiffres)
- Code commune INSEE
- Département (code sur 2 ou 3 caractères)

**Données économiques :**
- Chiffre d'affaires annuel total en euros
- Chiffre d'affaires éthique (CA des médicaments prescrits) en euros
- Chiffre d'affaires conseil (CA de tous les produits hors prescriptions : parapharmacie, cosmétiques, compléments alimentaires, hygiène) en euros
- Le delta est calculé automatiquement : CA total - CA éthique - CA conseil = CA des dispositifs médicaux hors prescription (capteurs de glycémie, tensiomètres, bas de contention, orthopédie, maintien à domicile)

**Caractéristiques géographiques :**
- Type de zone géographique : urbain dense, urbain, périurbain ou rural (cette classification peut être déduite automatiquement de la localisation si elle n'est pas fournie, en utilisant la grille de densité INSEE)

Ces informations permettent de calculer le score de taille S via la transformation logarithmique du chiffre d'affaires total, et le score de mix CA en calculant la proportion du CA provenant des segments pertinents pour les seniors. Concrètement, le mix CA 65+ est calculé comme suit : (CA éthique + Delta) / CA total. En effet, le CA éthique (médicaments prescrits) et le delta (dispositifs médicaux) sont les deux composantes les plus pertinentes pour la clientèle senior, contrairement au CA conseil qui inclut une large part de produits cosmétiques, d'hygiène courante et de parapharmacie non spécifiques aux seniors. Un ratio élevé indique une pharmacie orientée santé et dispositifs médicaux, donc potentiellement plus attractive pour les 65+. Le type de zone géographique détermine le coefficient beta de décroissance par la distance utilisé dans les calculs d'attractivité.

Les données proviennent généralement des systèmes d'information internes des groupements ou réseaux de pharmacies, des logiciels de gestion officinale, ou peuvent être achetées auprès de fournisseurs spécialisés en données de marché pharmaceutique. La qualité et la complétude de ces données sont cruciales pour la fiabilité du modèle. En particulier, la précision de la géolocalisation (latitude/longitude) doit être au mètre près, car elle conditionne le calcul des isochrones et l'identification des hubs de proximité.

### Données sur les zones IRIS

Pour chaque zone IRIS, on a besoin de la population totale et de sa décomposition par tranche d'âge (65-74, 75-84, 85+) et par genre. Ces données sont disponibles sur le site de l'INSEE et sont mises à jour lors de chaque recensement. On a également besoin du contour géographique de chaque IRIS sous forme de polygone, disponible dans les fichiers CONTOURS-IRIS de l'INSEE.

Le revenu médian de chaque IRIS est également utilisé pour le calcul du facteur socio-économique. Ces données sont publiées par l'INSEE avec un certain décalage temporel (environ 2 ans). Enfin, la densité de professionnels de santé par IRIS ou par commune peut être calculée à partir du répertoire RPPS mis à disposition publiquement.

### Données sur les hubs et points d'intérêt

Les établissements de santé (hôpitaux, cliniques, EHPAD, centres de rééducation) sont disponibles dans le fichier FINESS, accessible en open data. Les commerces, marchés, et autres points d'intérêt sont extraits d'OpenStreetMap via des requêtes ciblées (tags amenity, shop, healthcare, etc.). Les arrêts de transports en commun sont récupérés via les APIs des opérateurs de transport ou via OpenStreetMap.

Ces données doivent être géolocalisées précisément et associées à des catégories homogènes pour permettre le calcul des bonus d'attractivité. Un travail de nettoyage et de dédoublonnage est souvent nécessaire, car les sources peuvent être redondantes ou contenir des erreurs.

### Données d'isochrones

Les isochrones sont calculées en utilisant les données de réseau routier et piétonnier d'OpenStreetMap. Elles nécessitent également des hypothèses sur les vitesses de déplacement : par exemple, 4 km/h à pied pour un senior, 30 km/h en voiture en zone urbaine, 50 km/h en zone rurale. Ces hypothèses peuvent être affinées en fonction de données de trafic réelles si elles sont disponibles.

Les isochrones sont stockées sous forme de fichiers géographiques (GeoJSON, Shapefile) et organisées par pharmacie et par temps de trajet. Leur taille totale peut être importante (plusieurs gigaoctets), d'où l'importance d'une gestion efficace du stockage et du cache.

### Coefficients et paramètres du modèle

Enfin, le modèle repose sur un ensemble de coefficients et de paramètres qui doivent être définis et maintenus dans des fichiers de configuration. Ces paramètres incluent les poids des facteurs locaux (α1 à α4), les bonus des hubs, les facteurs de mobilité par âge, les coefficients beta par type de zone, les paniers moyens Rx et Para, les ratios régionaux, etc.

Ces paramètres sont typiquement regroupés dans des tableaux structurés qui facilitent leur lecture et leur modification. Le tableau ci-dessous récapitule les principaux paramètres du modèle :

| Paramètre | Valeur | Justification | Source |
|-----------|--------|---------------|--------|
| CA référence S_j | 500 000 € | CA médian France | Données internes |
| Borne min S_j | -0.5 | Éviter valeurs extrêmes | Calibration |
| Borne max S_j | 1.0 | Éviter valeurs extrêmes | Calibration |
| Poids densité médicale α₁ | 0.30 | Le plus important pour 65+ | Expert |
| Poids socio-éco α₂ | 0.20 | Impact modéré | Expert |
| Poids mix CA α₃ | 0.25 | Spécificité 65+ | Expert |
| Poids densité 65+ α₄ | 0.25 | Effet écosystème | Expert |
| Pondération cardio | 1.5 | Pathologies 65+ | CNAM |
| Pondération rhumato | 1.3 | Arthrose 65+ | CNAM |
| Densité médicale cible | 2.5 / 1000 | Bon maillage France | ARS |
| Revenu médian national | 22 000 €/an | Référence INSEE | INSEE 2023 |
| Bonus EHPAD | +25 % | Génération flux 75+ | Observation |
| Bonus marché | +20 % | Rituel social 65+ | Observation |
| Bonus bus | +15 % | Accessible PMR | Observation |
| Bonus métro | +8 % | Escaliers = obstacle | Observation |
| Plafond hub par catégorie | 25 % | Éviter surestimation | Calibration |
| Plafond hub global | 50 % | Éviter surestimation | Calibration |
| Mobilité 65-74 | 1.00 | Autonomes | INSEE mobilité |
| Mobilité 75-84 | 0.70 | Mobilité réduite | INSEE mobilité |
| Mobilité 85+ | 0.50 | Très limité | INSEE mobilité |
| Beta urbain dense | 1.6 | Alternatives nombreuses | Calibration |
| Beta urbain | 1.8 | Standard | Calibration |
| Beta périurbain | 2.0 | Moins d'alternatives | Calibration |
| Beta rural | 2.2 | Distance critique | Calibration |
| Ajustement beta 85+ | +0.30 | Très sensibles distance | Expert |
| Saisonnalité balnéaire été | ×1.9 | Afflux touristique | Données métier |
| Saisonnalité montagne hiver | ×1.8 | Ski | Données métier |
| Saisonnalité thermal | ×1.25 | Cures | Données métier |
| Panier Rx 65-74 | 850 €/an | Moyenne CNAM | CNAM |
| Panier Rx 75-84 | 1 200 €/an | Chroniques | CNAM |
| Panier Rx 85+ | 1 500 €/an | Polypathologies | CNAM |
| Panier Para 65-74 | 180 €/an | Prévention | Études marché |
| Panier Para 75-84 | 140 €/an | Baisse esthétique | Études marché |
| Panier Para 85+ | 100 €/an | Essentiel seul | Études marché |
| Ratio femmes | 56 % | Démographie INSEE | INSEE |
| Ratio hommes | 44 % | Démographie INSEE | INSEE |
| Ajustement Rx hommes | +10 % | Pathologies cardio | CNAM |
| Ajustement Para femmes | +15 % | Cosmétiques | Études marché |

---

## DONNÉES DE SORTIE PRODUITES

### Fichier principal par pharmacie

Le modèle produit pour chaque pharmacie un ensemble complet de métriques qui sont exportées dans un fichier CSV structuré. Les colonnes principales incluent l'identifiant unique de la pharmacie, ses coordonnées géographiques, son type de zone, son département, et bien sûr l'ensemble des résultats de calcul.

Les résultats de population captée sont fournis au total et décomposés par tranche d'âge (65-74 ans, 75-84 ans, 85 ans et plus) et par genre (femmes, hommes). Cela représente six colonnes numériques de population. Par exemple, une pharmacie pourra avoir capté 1 200 seniors au total, dont 500 dans la tranche 65-74 ans, 450 dans la tranche 75-84 ans, et 250 dans la tranche 85+, avec une répartition de 670 femmes et 530 hommes.

Les résultats de chiffre d'affaires théorique sont fournis au total et décomposés entre Rx et parapharmacie, ainsi que par genre. Cela représente cinq colonnes de CA en euros. Par exemple, une pharmacie pourra avoir un CA théorique 65+ total de 950 000 euros, dont 700 000 euros en Rx et 250 000 euros en parapharmacie, avec 560 000 euros pour les femmes et 390 000 euros pour les hommes.

Des métriques qualitatives complètent ces résultats : le score d'attractivité moyen de la pharmacie (moyenne pondérée sur toutes les zones qu'elle couvre), sa part de marché moyenne, le nombre de zones IRIS couvertes par sa zone de chalandise, et le nombre moyen de concurrents auxquels elle fait face. Ces indicateurs permettent de caractériser le positionnement concurrentiel de la pharmacie.

Enfin, des colonnes de contexte sont ajoutées pour faciliter l'interprétation : le type de zone touristique (balnéaire, montagne, thermal, standard), le type régional (urbain aisé, rural vieillissant, etc.), les ratios Rx et Para appliqués, et les valeurs moyennes des composantes de l'attractivité (S, F, H, M, beta). Ces informations contextuelles sont précieuses pour comprendre pourquoi telle ou telle pharmacie présente un potentiel élevé ou faible.

Le format final comprend 18 colonnes essentielles qui sont structurées de manière à être facilement exploitables par des outils de business intelligence, de visualisation cartographique, ou de statistiques descriptives. Ce fichier CSV constitue la livrable principal du modèle et peut être enrichi ou agrégé selon les besoins métier.

### Fichiers complémentaires et de diagnostic

En complément du fichier principal, le modèle peut générer plusieurs fichiers annexes qui facilitent l'audit, le débogage et l'analyse approfondie. Un fichier de détail par couple (pharmacie, zone IRIS) peut être produit, listant pour chaque interaction le score d'attractivité, la part de marché, la population captée, et les différentes composantes du calcul. Ce fichier est très volumineux (potentiellement plusieurs millions de lignes) mais extrêmement utile pour comprendre finement les mécanismes du modèle et identifier d'éventuelles anomalies.

Un fichier listant les hubs impactants par pharmacie peut également être généré, indiquant pour chaque pharmacie quels établissements de santé, quels transports, quels commerces ont contribué au bonus d'attractivité. Cela permet de visualiser l'environnement de chaque pharmacie et de comprendre son positionnement.

Un rapport de validation au format JSON ou texte synthétise les métriques qualité globales : taux de conservation de la population, nombre de pharmacies ayant un potentiel nul ou anormalement élevé, cohérence des distributions d'âge et de genre, écarts entre CA projeté et CA observé lorsque celui-ci est disponible. Ce rapport est essentiel pour valider que le modèle produit des résultats plausibles et cohérents avant toute utilisation opérationnelle ou diffusion.

Enfin, un fichier de cache des intersections isochrones/IRIS au format pickle peut être sauvegardé pour réutilisation ultérieure, permettant de gagner du temps lors des exécutions suivantes du modèle ou lors de simulations de scénarios alternatifs.

---

## CONTRÔLE QUALITÉ ET SEUILS D'ALERTE

Le modèle intègre un ensemble de contrôles qualité et de seuils d'alerte qui permettent de détecter automatiquement des résultats aberrants ou des incohérences dans les données. Ces contrôles sont essentiels pour garantir la fiabilité des projections et éviter des décisions erronées basées sur des calculs faussés.

Un premier contrôle porte sur la population captée : si une pharmacie présente une population 65+ captée supérieure à 10 000 personnes, une alerte est levée car cela pourrait indiquer une erreur de calcul ou une surestimation de l'attractivité. À l'inverse, si une pharmacie a une population captée inférieure à 100 seniors, une alerte de niveau bas est déclenchée, ce qui peut être normal pour une pharmacie en zone très rurale mais mérite vérification.

Un second contrôle compare, lorsque cela est possible, le CA théorique projeté avec le CA réel observé. Si l'écart entre les deux dépasse 30 %, une investigation est nécessaire pour comprendre si cela provient de spécificités locales non capturées par le modèle, d'erreurs dans les données d'entrée, ou d'un problème de calibration des paramètres. De tels écarts peuvent aussi révéler des opportunités de croissance ou au contraire des menaces concurrentielles.

Les ratios démographiques font également l'objet de contrôles. Le ratio femmes/hommes devrait théoriquement se situer entre 52 % et 60 % pour la population 65+, en cohérence avec les données INSEE. Si une pharmacie présente un ratio en dehors de cette fourchette, cela peut signaler une anomalie dans la répartition de la population des zones IRIS couvertes ou un bug dans les calculs d'allocation.

La part de marché moyenne d'une pharmacie doit rester dans des limites raisonnables. Si elle dépasse 80 %, cela suggère une situation de quasi-monopole qui peut être légitime en zone isolée mais qui mérite d'être vérifiée. À l'inverse, une part de marché très faible peut indiquer une pharmacie en difficulté ou mal positionnée.

Le nombre de zones IRIS couvertes par une pharmacie ne devrait jamais être nul, sauf cas exceptionnels de pharmacies temporairement fermées ou d'erreurs de géolocalisation. De même, pour chaque zone IRIS, la somme des parts de marché de toutes les pharmacies concurrentes doit être égale à 1.0 (à une tolérance numérique près). Un écart sur cette somme signale une erreur dans l'implémentation du modèle de Huff.

Enfin, le taux de conservation de la population au niveau national ou régional est un indicateur clé de la qualité globale du modèle. Il mesure le rapport entre la somme des populations captées par toutes les pharmacies et la population totale 65+ des zones IRIS. Un taux supérieur à 95 % est attendu. Un taux inférieur peut signaler que certaines zones ne sont pas couvertes par aucune pharmacie, ce qui peut être problématique dans le contexte d'un modèle de couverture territoriale.

Le tableau ci-dessous récapitule les seuils de contrôle qualité :

| Indicateur | Seuil | Action |
|------------|-------|--------|
| Pop 65+ captée > 10 000 | Alerte haute | Vérifier données |
| Pop 65+ captée < 100 | Alerte basse | Zone très rurale ? |
| Écart CA réel/théorique > 30 % | Investigation | Anomalie |
| Ratio F/H hors [52%-60%] | Vérification | Données INSEE ? |
| Part marché moyenne > 80 % | Alerte | Monopole suspect |
| Nb zones couvertes = 0 | Erreur | Pharmacie isolée ? |
| Somme parts marché ≠ 1.0 | Erreur calcul | Debug Huff |
| Conservation population < 95 % | Warning | Zones non couvertes |

---

## GLOSSAIRE DES TERMES TECHNIQUES

Le modèle fait appel à plusieurs concepts techniques issus de la géographie, de l'économie spatiale et de la modélisation statistique. Pour faciliter la compréhension et la communication autour du projet, voici les définitions des principaux termes utilisés.

Une **zone IRIS** désigne un Îlot Regroupé pour l'Information Statistique, qui est la brique de base du découpage territorial de l'INSEE. Chaque IRIS regroupe environ 2 000 habitants et constitue la maille la plus fine pour laquelle des statistiques démographiques et socio-économiques sont disponibles publiquement. La France métropolitaine et d'outre-mer compte environ 50 000 zones IRIS.

Une **isochrone** est une ligne ou un polygone reliant tous les points accessibles depuis un point de départ donné en un temps de trajet fixé. Par exemple, une isochrone de 10 minutes à pied autour d'une pharmacie délimite l'ensemble des lieux que l'on peut atteindre en marchant 10 minutes depuis cette pharmacie. Les isochrones permettent de modéliser de manière réaliste les zones de chalandise en tenant compte des obstacles géographiques et des réseaux de transport.

Le **modèle de Huff** est un modèle gravitaire développé par David Huff dans les années 1960 pour prédire les parts de marché de commerces concurrents. Il postule que la probabilité qu'un consommateur choisisse un commerce est proportionnelle à son attractivité et inversement proportionnelle à sa distance. Ce modèle est largement utilisé en géomarketing pour l'implantation de points de vente et l'analyse de concurrence spatiale.

Le **ratio de couverture** (ou coverage ratio) mesure la proportion de la surface d'une zone IRIS qui est couverte par l'isochrone d'une pharmacie. Il est calculé en divisant l'aire de l'intersection entre le polygone de l'isochrone et le polygone de l'IRIS par l'aire totale de l'IRIS. Ce ratio, compris entre 0 et 1, permet de pondérer la population accessible depuis la pharmacie.

La **zone de chalandise** d'une pharmacie désigne l'ensemble des zones géographiques d'où elle peut attirer des clients. Dans notre modèle, elle correspond à l'ensemble des zones IRIS dont le centroïde ou la surface est au moins partiellement couverte par les isochrones de la pharmacie. La taille et la forme de la zone de chalandise dépendent du type de territoire (urbain, rural) et de la mobilité de la population cible.

La **part de marché** d'une pharmacie pour une zone donnée représente la proportion théorique de la population de cette zone qui fréquente cette pharmacie plutôt qu'une autre. Elle est calculée selon le modèle de Huff en divisant l'attractivité de la pharmacie par la somme des attractivités de toutes les pharmacies concurrentes couvrant cette zone. La part de marché est un nombre compris entre 0 et 1, et la somme des parts de marché de toutes les pharmacies pour une zone donnée est égale à 1.

Le score **d'attractivité** est un indicateur composite qui mesure le pouvoir d'attraction d'une pharmacie pour les seniors d'une zone donnée. Il combine plusieurs dimensions : la taille de la pharmacie, son environnement médical et socio-économique, la présence de hubs de proximité, la mobilité de la population cible, et la distance qui sépare la zone de la pharmacie. L'attractivité est exprimée sur une échelle de 0 à 5, avec des valeurs typiques autour de 1 à 2 pour des pharmacies moyennes.

**OSMnx** est une bibliothèque Python développée pour faciliter l'analyse des réseaux de transport urbain à partir des données d'OpenStreetMap. Elle permet de télécharger automatiquement les graphes routiers, piétonniers et cyclables d'une zone géographique, puis d'appliquer des algorithmes de recherche de plus court chemin et de calcul d'isochrones. OSMnx est devenue un outil standard en analyse spatiale et en géomarketing.

Le **répertoire RPPS** (Répertoire Partagé des Professionnels de Santé) est une base de données publique qui recense l'ensemble des professionnels de santé exerçant en France. Elle contient pour chaque praticien son identité, sa spécialité, et ses lieux d'exercice avec leurs coordonnées géographiques. Le RPPS est une source essentielle pour cartographier la densité médicale et calculer les facteurs locaux du modèle.

Le fichier **FINESS** (Fichier National des Établissements Sanitaires et Sociaux) est une base de données publique qui répertorie l'ensemble des établissements et services du secteur sanitaire et médico-social en France : hôpitaux, cliniques, EHPAD, centres de soins, etc. Chaque établissement est géolocalisé et catégorisé, ce qui permet d'identifier les hubs de santé à proximité des pharmacies.

---

## CONCLUSION

Ce document présente de manière exhaustive la méthodologie de calcul du potentiel 65+ des pharmacies françaises. Le modèle développé constitue un outil d'aide à la décision puissant et robuste, permettant d'estimer avec précision le nombre de clients seniors potentiels et le chiffre d'affaires théorique associé pour chaque pharmacie du territoire.

L'approche en trois phases, combinant attractivité composite, modèle de Huff et projection de chiffre d'affaires, offre une grande finesse d'analyse tout en restant techniquement maîtrisable. La prise en compte des spécificités territoriales, de la mobilité des seniors, de l'environnement médical et commercial, et de la saisonnalité garantit que les projections sont ancrées dans les réalités de terrain.

La granularité des résultats, avec la décomposition par tranche d'âge et par genre, permet des analyses détaillées et des actions ciblées. La transparence de la méthodologie et la documentation exhaustive des paramètres facilitent l'appropriation du modèle par les utilisateurs et permettent des ajustements et des calibrations en fonction des retours d'expérience.

Les contrôles qualité intégrés et les fichiers de diagnostic produits offrent les garanties nécessaires pour une utilisation opérationnelle en toute confiance. Le modèle peut servir de base pour des simulations de scénarios (ouverture de nouvelles pharmacies, fermetures, évolutions démographiques), des benchmarks concurrentiels, ou des optimisations de gammes de produits.

Ce travail s'inscrit dans une démarche d'amélioration continue : les paramètres pourront être affinés au fur et à mesure de la collecte de données de validation, les sources de données pourront être enrichies (données de mobilité réelle, enquêtes de satisfaction), et de nouvelles dimensions pourront être intégrées (fidélité, services additionnels, téléconsultation).

---

**FIN DU DOCUMENT MÉTHODOLOGIQUE DÉTAILLÉ**
