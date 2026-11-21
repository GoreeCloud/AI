package com.goreecloud.ai

/** Pure request bounds for native token efficiency controls. No network/state. */
internal object NativeTokenPolicy {
    fun recentCount(value: Int): Int = if (value in setOf(4, 8, 16)) value else 8

    fun outputCap(value: Int): Int = if (value in setOf(256, 512, 1024, 2048)) value else 2048

    fun providerResponseCache(provider: String, cloudConsent: Boolean, enabled: Boolean): Boolean =
        enabled && cloudConsent && provider != "ollama"
}
