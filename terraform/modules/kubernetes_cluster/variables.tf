variable "cluster_name" {
  type        = string
  description = "Nombre del clúster de Kubernetes"
}

variable "node_image" {
  type        = string
  description = "Imagen del nodo de Kubernetes para Kind"
  default     = "kindest/node:v1.30.0"
}

variable "worker_count" {
  type        = number
  description = "Cantidad de worker nodes en el clúster"
  default     = 2
}

variable "host_http_port" {
  type        = number
  description = "Puerto del host mapeado al puerto 80 del clúster"
  default     = 80
}

variable "host_https_port" {
  type        = number
  description = "Puerto del host mapeado al puerto 443 del clúster"
  default     = 443
}