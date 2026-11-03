output "cluster_name" {
  description = "Nombre del clúster Kind"
  value       = module.kubernetes_cluster.cluster_name
}

output "cluster_endpoint" {
  description = "Endpoint del clúster de Kubernetes"
  value       = module.kubernetes_cluster.endpoint
}