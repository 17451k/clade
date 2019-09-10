from django.urls import path

from . import views

app_name = 'cmds'
urlpatterns = [
    path('', views.cmds, name='cmds'),
    path('<int:cmd_id>/', views.cmd, name='cmd'),
    path('<int:cmd_id>/pid_graph', views.pid_graph, name='pid_graph'),
    path('<int:cmd_id>/pid_graph/load', views.load_pid_graph, name='load_pid_graph'),
    path('<int:cmd_id>/pid_graph_lazy', views.pid_graph_lazy, name='pid_graph_lazy'),
    path('<int:cmd_id>/pid_graph_lazy/load', views.load_pid_graph_lazy, name='load_pid_graph_lazy'),
    path('<int:cmd_id>/pid_graph_lazy/load_node', views.load_pid_graph_node, name='load_pid_graph_node'),
    path('<int:cmd_id>/cmd_graph', views.cmd_graph, name='cmd_graph'),
    path('<int:cmd_id>/cmd_graph/load', views.load_cmd_graph, name='load_cmd_graph'),
]
