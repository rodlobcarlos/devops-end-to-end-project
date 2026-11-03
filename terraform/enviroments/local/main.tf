provider "kind" {}

module "kubernetes_cluster" {
  source = "../../modules/kubernetes_cluster"

  cluster_name = var.cluster_name
  worker_count = var.worker_count
}

provider "kubernetes" {
  host                   = module.kubernetes_cluster.endpoint
  client_certificate     = module.kubernetes_cluster.client_certificate
  client_key             = module.kubernetes_cluster.client_key
  cluster_ca_certificate = module.kubernetes_cluster.cluster_ca_certificate
}