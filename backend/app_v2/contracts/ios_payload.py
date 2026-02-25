from typing import List, Optional

from pydantic import BaseModel, Field



class IOSBBox(BaseModel):
    x: float
    y: float
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)

class IOSDocumentRef(BaseModel):
    partId: str
    partType: str

class IOSCanvasImage(BaseModel):
    mimeType: str
    fileExtension: str
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    dataBase64: str = Field(..., min_length=1)


class IOSWordLocation(BaseModel):
    label: str
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    candidates: Optional[List[str]] = None
    strokeIds: Optional[List[str]] = None


class IOSProvisionalStep(BaseModel):
    stepId: str
    text: str = Field(..., min_length=1)
    elementType: str
    bbox: Optional[IOSBBox] = None
    wordLocations: Optional[List[IOSWordLocation]] = None
    strokeIds: List[str] = Field(default_factory=list)
    lineIndex: int = Field(..., ge=0)


class IOSRecognitionPayload(BaseModel):
    mimeType: str
    rawJiix: Optional[str] = None
    transcriptionText: Optional[str] = None
    wordLocations: Optional[List[IOSWordLocation]] = None
    provisionalSteps: Optional[List[IOSProvisionalStep]] = None


class IOSClientMeta(BaseModel):
    device: str
    appVersion: str
    canvasWidth: float = Field(..., gt=0)
    canvasHeight: float = Field(..., gt=0)
    viewScale: float = Field(..., gt=0)
    viewOffsetX: float
    viewOffsetY: float
    coordinateSpace: str


class IOSAnalyzePayload(BaseModel):
    requestId: str
    sessionId: str = Field(..., min_length=1)
    timestampMs: int = Field(..., gt=0)


    document: IOSDocumentRef
    recognition: IOSRecognitionPayload
    clientMeta: IOSClientMeta

    canvasImage: Optional[IOSCanvasImage] = None



    exportedDataBase64: Optional[str] = None

    #snapshots
    snapshotId: str = Field(..., min_length=1)
    lastSnapshotId: Optional[str] = None

