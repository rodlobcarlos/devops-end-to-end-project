variable "environment" {
  type        = string
  description = "Nombre del entorno de despliegue"
  default     = "local"
}

variable "cluster_name" {
  type        = string
  description = "Nombre del clúster"
  default     = "devops-showcase-local"
}

variable "worker_count" {
  type        = number
  description = "Número de worker nodes para local"
  default     = 2
}