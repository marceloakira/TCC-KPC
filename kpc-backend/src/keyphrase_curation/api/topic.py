from fastapi import APIRouter, Depends, HTTPException
from keyphrase_curation.util.security import get_current_user
from keyphrase_curation.controller.user_attribution \
    import UserAttributionController
from keyphrase_curation.controller.annotation \
    import AnnotationController
from keyphrase_curation.model.annotation import \
    AnnotationTask, KeyphraseCurationFile
from keyphrase_curation import config
from typing import Dict, List, Tuple, Optional
from keyphrase_curation.model.keyphrase import KeyphraseSorting
from keyphrase_curation.model.cluster import ClusterSorting
# @model: specs/002-pairwise-similarity-fix/model/classes.puml
# RF: RF-003 — Conversão numpy → Python nativo no retorno da API
from keyphrase_curation.util.json_encoder import NumpyConverter

router = APIRouter()


# ============================================================================
# Funções auxiliares
# ============================================================================

def _generate_default_alias(keyphrase1: str, keyphrase2: str) -> str:
    """Gera o alias padrão baseado nas keyphrases selecionadas."""
    kp1 = keyphrase1.strip().lower().replace(" ", "_") if keyphrase1 else ""
    kp2 = keyphrase2.strip().lower().replace(" ", "_") if keyphrase2 else ""
    
    if kp1 and kp2:
        return f"{kp1}_and_{kp2}"
    elif kp1:
        return kp1
    return ""


def _process_keyphrases_selection(keyphrases_sel_obj: Optional[dict]) -> list:
    """Processa o objeto de seleção de keyphrases e retorna como array."""
    if isinstance(keyphrases_sel_obj, dict):
        return [
            keyphrases_sel_obj.get("selected1", ""),
            keyphrases_sel_obj.get("selected2", ""),
            keyphrases_sel_obj.get("keyphrase1", ""),
            keyphrases_sel_obj.get("keyphrase2", "")
        ]
    return []


def _create_keyphrases_aliases_obj(keyphrases_sel: list, alias_original: str) -> dict:
    """Cria o objeto de aliases com default e alias customizado."""
    default_alias = ""
    if keyphrases_sel and len(keyphrases_sel) >= 4:
        default_alias = _generate_default_alias(
            keyphrases_sel[2], 
            keyphrases_sel[3]
        )
    
    return {
        "default": default_alias,
        "alias": alias_original if alias_original else ""
    }


def _build_cluster_object(
    cluster_id: str,
    cluster_data: any,
    cluster_selection: dict,
    keyphrases_selection: dict,
    keyphrases_aliases: dict
) -> dict:
    """Constrói um objeto de cluster completo."""
    cluster_sel = cluster_selection.get(str(cluster_id), None)
    
    keyphrases_sel_obj = keyphrases_selection.get(str(cluster_id), None)
    keyphrases_sel = _process_keyphrases_selection(keyphrases_sel_obj)
    
    alias_original = keyphrases_aliases.get(str(cluster_id), "")
    keyphrases_ali = _create_keyphrases_aliases_obj(keyphrases_sel, alias_original)
    
    return {
        "cluster_id": cluster_id,
        "cluster_data": cluster_data,
        "cluster_selection": cluster_sel,
        "keyphrases_selection": keyphrases_sel,
        "keyphrases_aliases": keyphrases_ali
    }


def _has_valid_keyphrases(cluster: dict) -> bool:
    """Verifica se o cluster tem keyphrases_selection não vazias."""
    kp_sel = cluster.get("keyphrases_selection", [])
    return (kp_sel and len(kp_sel) >= 4 and
            (kp_sel[0] or kp_sel[1] or kp_sel[2] or kp_sel[3]))


def _apply_custom_sorting(clusters_array: list, sorting_type: str) -> list:
    """Aplica sorting customizado aos clusters."""
    if sorting_type == "alphabetical_cluster_alias":
        # Filtrar clusters com keyphrases_selection vazias
        filtered = [c for c in clusters_array if _has_valid_keyphrases(c)]
        # Ordenar alfabeticamente pelo alias
        filtered.sort(key=lambda x: (
            x["keyphrases_aliases"]["alias"] if x["keyphrases_aliases"]["alias"] 
            else x["keyphrases_aliases"]["default"]
        ).lower())
        return filtered
    
    elif sorting_type == "numerical_cluster_alias":
        # Filtrar clusters com keyphrases_selection vazias
        filtered = [c for c in clusters_array if _has_valid_keyphrases(c)]
        # Ordenar numericamente pelo cluster_id
        filtered.sort(key=lambda x: int(x["cluster_id"]) if str(x["cluster_id"]).isdigit() else float('inf'))
        return filtered
    
    return clusters_array


def _process_clusters_to_array(
    clusters: dict,
    cluster_selection: dict,
    keyphrases_selection: dict,
    keyphrases_aliases: dict,
    sorting_type: Optional[str] = None
) -> list:
    """Processa os clusters de dict para array com todos os dados."""
    if not isinstance(clusters, dict):
        return clusters
    
    clusters_array = []
    for cluster_id, cluster_data in clusters.items():
        cluster_obj = _build_cluster_object(
            cluster_id,
            cluster_data,
            cluster_selection,
            keyphrases_selection,
            keyphrases_aliases
        )
        clusters_array.append(cluster_obj)
    
    # Aplicar sorting customizado se necessário
    if sorting_type in ["alphabetical_cluster_alias", "numerical_cluster_alias"]:
        clusters_array = _apply_custom_sorting(clusters_array, sorting_type)
    
    return clusters_array


# ============================================================================
# Rotas da API
# ============================================================================


@router.get("/{username}/list")
@router.get("/{username}/list/", include_in_schema=False)
async def list_topics(
        username: str,
        logged_user: str = Depends(get_current_user)
    ) -> dict:

    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        topics = UserAttributionController().get_topics(username)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"topics": topics}

@router.get("/keyphrase_clustering/{username}/{topic}")
@router.get("/keyphrase_clustering/{username}/{topic}/{keyphrase_order}")
async def list_keyphrase_clusters(
        username: str,
        topic: str,
        keyphrase_order: str = None,
        logged_user: str = Depends(get_current_user)
    ) -> dict:

    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        topics_user = UserAttributionController().get_topics(username)
        if topic not in topics_user:
            raise HTTPException(status_code=404, detail="Topic not found")

        if keyphrase_order is None or keyphrase_order not in [ks.value for ks in KeyphraseSorting]:
            keyphrase_order = KeyphraseSorting.ALPHABETICAL.value
        
        sorting = KeyphraseSorting.by_value(keyphrase_order)
        
        ac = AnnotationController(topic, username)
        keyphrase_clustering = ac.get_keyphrase_clustering(sorting)
        
        # Converter objeto para array para garantir ordem em todos os clientes
        if isinstance(keyphrase_clustering, dict):
            # Converter para array mantendo a ordem que vem do backend
            clusters_array = []
            for cluster_id, cluster_data in keyphrase_clustering.items():
                cluster_obj = {"id": cluster_id}
                if isinstance(cluster_data, dict):
                    cluster_obj.update(cluster_data)
                else:
                    cluster_obj["data"] = cluster_data
                clusters_array.append(cluster_obj)
            
            keyphrase_clustering = clusters_array

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "sorting": sorting.value,
        "clusters": keyphrase_clustering
    }

@router.get("/clusters/{username}/{topic}")
@router.get("/clusters/{username}/{topic}/{cluster_order}")
async def list_clusters(
        username: str,
        topic: str,
        cluster_order: str = None,
        logged_user: str = Depends(get_current_user)
    ) -> dict:

    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        topics_user = UserAttributionController().get_topics(username)
        if topic not in topics_user:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Validar cluster_order e definir sorting padrão
        valid_orders = [cs.value for cs in ClusterSorting] + ["alphabetical_cluster_alias", "numerical_cluster_alias"]
        cluster_order_original = cluster_order

        if cluster_order is None or cluster_order not in valid_orders:
            cluster_order = ClusterSorting.NUMERICAL.value
        
        # Determinar sorting base
        if cluster_order_original in ["alphabetical_cluster_alias", "numerical_cluster_alias"]:
            sorting = ClusterSorting.NUMERICAL
        else:
            sorting = ClusterSorting.by_value(cluster_order)

        # RF: "Dicas de Outros Anotadores" somente para perfil adjudicator
        if sorting == ClusterSorting.CLUES_FROM_OTHER_ANNOTATORS:
            annotation_profile = \
                UserAttributionController().get_annotation_profile(
                    username, topic)
            if annotation_profile != "adjudicator":
                raise HTTPException(
                    status_code=403,
                    detail="clues_from_other_annotators sorting is only "
                           "allowed for adjudicator profile")

        ac = AnnotationController(topic, username)
        clusters, clusters_meta_info = ac.get_clusters(sorting)
        cluster_selection = ac.get_cluster_selection()
        keyphrases_selection = ac.get_keyphrases_selection()
        keyphrases_aliases = ac.get_keyphrases_aliases()
        
        # Processar clusters para array
        clusters = _process_clusters_to_array(
            clusters,
            cluster_selection,
            keyphrases_selection,
            keyphrases_aliases,
            cluster_order_original
        )
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # @model: specs/002-pairwise-similarity-fix/model/classes.puml
    # RF: RF-003-C1 — Converter tipos numpy em TODO o dicionário de retorno
    return NumpyConverter.to_native({
        "sorting_applied": sorting.value,
        "clusters": clusters,
        "clusters_meta_info": clusters_meta_info
    })


@router.get("/cluster_selection/{username}/{topic}")
async def list_cluster_selection(
        username: str,
        topic: str,
        logged_user: str = Depends(get_current_user)
    ) -> dict:
    
    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        topics_user = UserAttributionController().get_topics(username)
        if topic not in topics_user:
            raise HTTPException(status_code=404, detail="Topic not found")
        ac = AnnotationController(topic, username)
        cluster_selection = ac.get_cluster_selection()
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return cluster_selection

@router.get("/keyphrases_selection/{username}/{topic}")
async def list_keyphrases_selection(
        username: str,
        topic: str,
        logged_user: str = Depends(get_current_user)
    ) -> dict:
    
    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        topics_user = UserAttributionController().get_topics(username)
        if topic not in topics_user:
            raise HTTPException(status_code=404, detail="Topic not found")
        ac = AnnotationController(topic, username)
        keyphrases_selection = ac.get_keyphrases_selection()
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return keyphrases_selection

@router.get("/keyphrases_aliases/{username}/{topic}")
async def list_keyphrases_aliases(
        username: str,
        topic: str,
        logged_user: str = Depends(get_current_user)
    ) -> dict:

    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        topics_user = UserAttributionController().get_topics(username)
        if topic not in topics_user:
            raise HTTPException(status_code=404, detail="Topic not found")
        ac = AnnotationController(topic, username)
        keyphrases_aliases = ac.get_keyphrases_aliases()
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return keyphrases_aliases

@router.get("/annotation_profile/{username}/{topic}")
async def get_annotation_profile(
        username: str,
        topic: str,
        logged_user: str = Depends(get_current_user)
    ) -> dict:

    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        topics_user = UserAttributionController().get_topics(username)
        if topic not in topics_user:
            raise HTTPException(status_code=404, detail="Topic not found")

        uac = UserAttributionController()
        annotation_profile = uac.get_annotation_profile(username, topic)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"annotation_profile": annotation_profile}


def _get_adjudicator_clusters_data(username: str, topic: str) -> dict:
    """Monta os dados de adjudicação no formato esperado pelo frontend:
    {
      adjudicator: {clusterId: [desc, [kp...]]},
      annotator1:  {clusterId: [desc, [kp...]]},
      annotator2:  {clusterId: [desc, [kp...]]},
      union:       {clusterId: [desc, [kp...]]},
    }

    Os clusters do adjudicator são lidos do arquivo de anotação do próprio
    adjudicator; os dos anotadores, dos arquivos declarados como 'sources'
    na atribuição do adjudicator (annotations/<user1>/<topic>.kpc e
    annotations/<user2>/<topic>.kpc).
    """
    uac = UserAttributionController()
    annotation_files = uac.get_annotation_files(username, topic)

    # Fontes dos anotadores (adjudicator usa 'sources' em vez de 'source')
    sources = annotation_files.get('sources', [])
    if len(sources) < 2:
        raise ValueError(
            "Adjudicator attribution must have at least 2 sources")

    def load_clusters(filepath: str) -> dict:
        """Carrega clusters {cluster_id: [desc, [kp...]]} de um arquivo .kpc"""
        kpc = KeyphraseCurationFile(filepath)
        data = kpc.get_data_from_json(check_consistency=False)
        clusters = {}
        for cluster_id, cluster in data['clusters'].items():
            keyphrases = [
                f"{data['keyphrases'][str(kp_id)]['keyphrase']}({kp_id})"
                for kp_id in cluster['keyphrases']
            ]
            clusters[str(cluster_id)] = [f"Cluster {cluster_id}", keyphrases]
        return clusters

    annotator1_clusters = load_clusters(
        config['dataset_path'] + '/' + sources[0])
    annotator2_clusters = load_clusters(
        config['dataset_path'] + '/' + sources[1])
    adjudicator_clusters = load_clusters(
        uac.get_annotation_filepaths(username, topic)['target'])

    # União das keyphrases dos dois anotadores por cluster
    union_clusters = {}
    for cluster_id in annotator1_clusters:
        kp1 = set(annotator1_clusters.get(cluster_id, [None, []])[1])
        kp2 = set(annotator2_clusters.get(cluster_id, [None, []])[1])
        union_clusters[cluster_id] = [
            f"Cluster {cluster_id}",
            sorted(kp1.union(kp2))
        ]

    return {
        "adjudicator": adjudicator_clusters,
        "annotator1": annotator1_clusters,
        "annotator2": annotator2_clusters,
        "union": union_clusters
    }


@router.get("/adjudicator_data/{username}/{topic}")
async def get_adjudicator_data(
        username: str,
        topic: str,
        logged_user: str = Depends(get_current_user)
    ) -> dict:

    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        uac = UserAttributionController()
        topics_user = uac.get_topics(username)
        if topic not in topics_user:
            raise HTTPException(status_code=404, detail="Topic not found")

        # Somente perfil adjudicator pode acessar os dados de adjudicação
        annotation_profile = uac.get_annotation_profile(username, topic)
        if annotation_profile != "adjudicator":
            raise HTTPException(
                status_code=403,
                detail="adjudicator_data is only allowed for "
                       "adjudicator profile")

        clusters_annotation_data = \
            _get_adjudicator_clusters_data(username, topic)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # @model: specs/002-pairwise-similarity-fix/model/classes.puml
    # RF: RF-003-C1 — Converter tipos numpy em TODO o dicionário de retorno
    return NumpyConverter.to_native(clusters_annotation_data)


@router.get("/get_annotation_task_options/{username}")
async def get_annotation_task_options(
        username: str, 
        logged_user: str = Depends(get_current_user)
    ) -> dict:
    
    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        options = [
            {"name": member.name, "value": member.value}
            for member in AnnotationTask
        ]
        return options
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/move_to_cluster/{username}/{topic}/{keyphrase_id}/{cluster_id}")
async def move_to_cluster(
        username: str,
        topic: str,
        keyphrase_id: str,
        cluster_id: str,
        logged_user: str = Depends(get_current_user)
    ) -> dict:
    
    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        topics_user = UserAttributionController().get_topics(username)
        if topic not in topics_user:
            raise HTTPException(status_code=404, detail="Topic not found")
        ac = AnnotationController(topic, username)
        ac.move_to_cluster(int(keyphrase_id), int(cluster_id))
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Keyphrase moved successfully"}

@router.put("/save_annotation/{username}/{topic}/{task}")
async def save_annotation(
        username: str,
        topic: str,
        task: str,
        logged_user: str = Depends(get_current_user)
    ) -> dict:

    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        topics_user = UserAttributionController().get_topics(username)
        if topic not in topics_user:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Convert string task to AnnotationTask enum
        try:
            annotation_task = AnnotationTask(task)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid task: {task}")
        
        ac = AnnotationController(topic, username)
        boSave = ac.save(annotation_task)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Annotation saved successfully", "saved": boSave}

@router.put("/move_to_cluster_and_save_annotation/{username}/{topic}/{keyphrase_id}/{cluster_id}")
@router.put("/move_to_cluster_and_save_annotation/{username}/{topic}/{keyphrase_id}/{cluster_id}/{task}")
async def move_to_cluster_and_save_annotation(
        username: str,
        topic: str,
        keyphrase_id: str,
        cluster_id: str,
        task: str = None,
        logged_user: str = Depends(get_current_user)
    ) -> dict:

    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        topics_user = UserAttributionController().get_topics(username)
        if topic not in topics_user:
            raise HTTPException(status_code=404, detail="Topic not found")
        if task is None or task not in [at.value for at in AnnotationTask]:
            task = AnnotationTask.KEYPHRASE_CLUSTERING.value
        ac = AnnotationController(topic, username)
        ac.move_to_cluster(int(keyphrase_id), int(cluster_id))
        boSave = ac.save(task=AnnotationTask(task))
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Keyphrase moved and annotation saved successfully", "saved": boSave}

@router.put("/select_cluster/{username}/{topic}/{cluster_id}/{selected}")
async def select_cluster(
        username: str,
        topic: str,
        cluster_id: str,
        selected: str,
        logged_user: str = Depends(get_current_user)
    ) -> dict:
    
    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        topics_user = UserAttributionController().get_topics(username)
        if topic not in topics_user:
            raise HTTPException(status_code=404, detail="Topic not found")
        ac = AnnotationController(topic, username)
        ac.select_cluster(int(cluster_id), int(selected))
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Cluster selection updated successfully"}

@router.put("/select_cluster_and_save_annotation/{username}/{topic}/{cluster_id}/{selected}")
@router.put("/select_cluster_and_save_annotation/{username}/{topic}/{cluster_id}/{selected}/{task}")
async def select_cluster_and_save_annotation(
        username: str,
        topic: str,
        cluster_id: str,
        selected: str,
        task: str = None,
        logged_user: str = Depends(get_current_user)
    ) -> dict:

    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        topics_user = UserAttributionController().get_topics(username)
        if topic not in topics_user:
            raise HTTPException(status_code=404, detail="Topic not found")
        if task is None or task not in [at.value for at in AnnotationTask]:
            task = AnnotationTask.CLUSTER_SELECTION.value
        ac = AnnotationController(topic, username)
        ac.select_cluster(int(cluster_id), int(selected))
        boSave = ac.save(task=AnnotationTask(task))
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Cluster selection updated and saved successfully", "saved": boSave}

@router.put("/select_keyphrase/{username}/{topic}/{cluster_id}/{order}/{keyphrase_id}")
async def select_keyphrase(
        username: str,
        topic: str,
        cluster_id: str,
        order: str,
        keyphrase_id: str,
        logged_user: str = Depends(get_current_user)
    ) -> dict:
    
    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        topics_user = UserAttributionController().get_topics(username)
        if topic not in topics_user:
            raise HTTPException(status_code=404, detail="Topic not found")
        ac = AnnotationController(topic, username)
        ac.select_keyphrase(int(cluster_id), int(order), int(keyphrase_id))
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Keyphrase selection updated successfully"}

@router.put("/select_keyphrase_and_save_annotation/{username}/{topic}/{cluster_id}/{order}/{keyphrase_id}")
@router.put("/select_keyphrase_and_save_annotation/{username}/{topic}/{cluster_id}/{order}/{keyphrase_id}/{task}")
async def select_keyphrase_and_save_annotation(
        username: str,
        topic: str,
        cluster_id: str,
        order: str,
        keyphrase_id: str,
        task: str = None,
        logged_user: str = Depends(get_current_user)
    ) -> dict:
    
    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        topics_user = UserAttributionController().get_topics(username)
        if topic not in topics_user:
            raise HTTPException(status_code=404, detail="Topic not found")
        if task is None or task not in [at.value for at in AnnotationTask]:
            task = AnnotationTask.KEYPHRASE_SELECTION.value
        ac = AnnotationController(topic, username)
        ac.select_keyphrase(int(cluster_id), int(order), int(keyphrase_id))
        boSave = ac.save(task=AnnotationTask(task))
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Keyphrase selection updated and saved successfully", "saved": boSave}

@router.put("/set_alias/{username}/{topic}/{cluster_id}/{alias}")
async def set_alias(
        username: str,
        topic: str,
        cluster_id: str,
        alias: str,
        logged_user: str = Depends(get_current_user)
    ) -> dict:

    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        topics_user = UserAttributionController().get_topics(username)
        if topic not in topics_user:
            raise HTTPException(status_code=404, detail="Topic not found")
        ac = AnnotationController(topic, username)
        ac.set_alias(int(cluster_id), alias)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Cluster alias updated successfully"}


@router.put("/set_alias_and_save_annotation/{username}/{topic}/{cluster_id}/{alias}")
@router.put("/set_alias_and_save_annotation/{username}/{topic}/{cluster_id}/{alias}/{task}")
async def set_alias_and_save_annotation(
        username: str,
        topic: str,
        cluster_id: str,
        alias: str,
        task: str = None,
        logged_user: str = Depends(get_current_user)
    ) -> dict:

    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        topics_user = UserAttributionController().get_topics(username)
        if topic not in topics_user:
            raise HTTPException(status_code=404, detail="Topic not found")
        if task is None or task not in [at.value for at in AnnotationTask]:
            task = AnnotationTask.KEYPHRASE_ALIAS.value
        ac = AnnotationController(topic, username)
        ac.set_alias(int(cluster_id), alias)
        boSave = ac.save(task=AnnotationTask(task))
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Cluster alias updated and saved successfully", "saved": boSave}


def _check_adjudicator_permission(username: str, topic: str):
    """Valida permissões e perfil adjudicator para os endpoints de adjudicação"""
    uac = UserAttributionController()
    topics_user = uac.get_topics(username)
    if topic not in topics_user:
        raise HTTPException(status_code=404, detail="Topic not found")
    annotation_profile = uac.get_annotation_profile(username, topic)
    if annotation_profile != "adjudicator":
        raise HTTPException(
            status_code=403,
            detail="adjudication is only allowed for adjudicator profile")


@router.put("/adjudicate/{username}/{topic}/{cluster_id}/{keyphrase_id}/{action}")
async def adjudicate(
        username: str,
        topic: str,
        cluster_id: str,
        keyphrase_id: str,
        action: str,
        logged_user: str = Depends(get_current_user)
    ) -> dict:

    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        _check_adjudicator_permission(username, topic)
        ac = AnnotationController(topic, username)
        ac.adjudicate(int(cluster_id), int(keyphrase_id), action)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Adjudication updated successfully"}


@router.put("/adjudicate_and_save/{username}/{topic}/{cluster_id}/{keyphrase_id}/{action}")
async def adjudicate_and_save(
        username: str,
        topic: str,
        cluster_id: str,
        keyphrase_id: str,
        action: str,
        logged_user: str = Depends(get_current_user)
    ) -> dict:

    if username != logged_user and logged_user != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        _check_adjudicator_permission(username, topic)
        ac = AnnotationController(topic, username)
        ac.adjudicate(int(cluster_id), int(keyphrase_id), action)
        boSave = ac.save_adjudication()
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Adjudication updated and saved successfully",
            "saved": boSave}
