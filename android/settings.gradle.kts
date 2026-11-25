pluginManagement {
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories { google(); mavenCentral() }
}
rootProject.name = "GoreeCloudAI"
include(":app", ":gc-ui-compose", ":gc-ui-shared")
project(":gc-ui-shared").projectDir = file("vendor/gc-ui/compose-multiplatform/gc-ui-compose")
