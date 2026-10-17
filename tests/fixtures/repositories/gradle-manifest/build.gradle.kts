plugins {
    java
}

repositories {
    mavenCentral()
}

dependencies {
    implementation("org.springframework:spring-context:6.2.0")
    implementation(project(":local"))
    // implementation("example:not-real:1.0")
}
