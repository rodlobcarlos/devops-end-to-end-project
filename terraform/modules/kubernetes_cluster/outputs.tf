output "endpoint" {
  description = "Endpoint del API server de Kubernetes"
  value       = kind_cluster.this.endpoint
}

output "cluster_name" {
  description = "Nombre del clúster generado"
  value       = kind_cluster.this.name
}

output "client_certificate" {
  description = "Certificado de cliente para autenticación"
  value       = kind_cluster.this.client_certificate
  sensitive   = true
}

output "client_key" {
  description = "Clave privada de cliente para autenticación"
  value       = kind_cluster.this.client_key
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "Certificado CA del clúster"
  value       = kind_cluster.this.cluster_ca_certificate
  sensitive   = true
}