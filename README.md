# Formulaire_IQM
Formulaire QField pour le calcul de l'IQM

## Intégration de du script à QGIS
Pour intégrer l'outil à QGIS, vous devez télécharger les scripts fournis et ajouter leur répertoire dans la section "Traitement" des options de QGIS.
Les scripts sont disponibles sur le [dépôt Github](https://github.com/Mehourka/QGIS-IQM) en clonant le dépôt ou en les téléchargeant sous format ".zip".

![Git_clone_zip](https://user-images.githubusercontent.com/84189822/227321703-39829cec-abfa-41dc-9d6c-d81cd4d0d401.png)

Une fois téléchargés, l'ajout des scripts à QGIS se fait comme suit :
- Ouvrez QGIS et cliquez sur l'option "Préférences" dans la barre de menus.
- Sélectionnez "Options" dans le menu déroulant.

![image1](https://user-images.githubusercontent.com/84189822/227153987-c880d5d2-b5e8-4606-8ed1-2b7a528285c4.png)

- Dans la boîte de dialogue Options de traitement, sélectionnez l'onglet "Scripts".
- Cliquez sur le bouton Ajouter à droite du champ pour ajouter le répertoire contenant les scripts et les modèles téléchargés.

![image3](https://user-images.githubusercontent.com/84189822/227154199-0191a4ed-2248-4cc6-93f4-ee73594d5919.png)

- Cliquez sur "OK" pour enregistrer les modifications.

Une fois ajouté dans le répertoire des scripts, l'algorithme Processing de l'outil sera disponible dans QGIS.

![image](https://user-images.githubusercontent.com/84189822/227292525-bc2e5ef8-59e1-4b1d-8b55-e095aedb0ec2.png)


## Utilisation de l’outil
Un ensemble de 15 scripts a été créé suite au développement des différents indicateurs, et les scripts exploitent l'interface de QGIS pour s’exécuter, effectuer l'analyse des données et afficher les résultats obtenus.

L’outil est structuré de la manière suivante :
- Le module **indicateurs_IQM** regroupe l'ensemble des scripts de calcul pour chaque indicateur de manière individuelle.
- Le module **IQM_utils** regroupe quant à lui les scripts et fonctions d'aide au prétraitement des données.
- L'algorithme principal **Calcul_IQM** a été conçu pour combiner les prétraitements et le calcul de tous les indicateurs.

![image](https://user-images.githubusercontent.com/84189822/227307189-d37efd2c-e010-461a-af50-fbe83b35c2d3.png)

