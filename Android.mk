LOCAL_PATH:= $(call my-dir)

include $(CLEAR_VARS)

LOCAL_MODULE := installer
LOCAL_MODULE_TAGS := optional

LOCAL_SRC_FILES := \
	        sources/main.c \

LOCAL_MODULE_PATH := $(LOCAL_PATH)

LOCAL_FORCE_STATIC_EXECUTABLE := true
LOCAL_STATIC_LIBRARIES := libc libcutils

include $(BUILD_EXECUTABLE)

include $(CLEAR_VARS)

LOCAL_MODULE := lkmod
LOCAL_MODULE_TAGS := optional

LOCAL_SRC_FILES := \
	        lkmod.c \

LOCAL_MODULE_PATH := $(LOCAL_PATH)

LOCAL_FORCE_STATIC_EXECUTABLE := true
LOCAL_STATIC_LIBRARIES := libc libcutils

include $(BUILD_EXECUTABLE)
