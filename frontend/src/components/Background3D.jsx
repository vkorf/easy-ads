import React, { useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, Environment, ContactShadows, Edges } from '@react-three/drei'

function FloatingShape({ position, rotation, scale, color, type }) {
    const meshRef = useRef()
    const [hovered, setHover] = useState(false)

    useFrame((state, delta) => {
        if (meshRef.current) {
            meshRef.current.rotation.x += delta * 0.2
            meshRef.current.rotation.y += delta * 0.1
        }
    })

    const renderGeometry = () => {
        switch (type) {
            case 'sphere': return <sphereGeometry args={[1, 32, 32]} />
            case 'cone': return <coneGeometry args={[1, 2, 32]} />
            case 'torus': return <torusGeometry args={[0.8, 0.3, 16, 32]} />
            case 'icosahedron': return <icosahedronGeometry args={[1, 0]} />
            case 'box': default: return <boxGeometry args={[1.5, 1.5, 1.5]} />
        }
    }

    return (
        <Float speed={2} rotationIntensity={1} floatIntensity={1}>
            <mesh
                ref={meshRef}
                position={position}
                rotation={rotation}
                scale={hovered ? [scale * 1.1, scale * 1.1, scale * 1.1] : [scale, scale, scale]}
                onPointerOver={() => setHover(true)}
                onPointerOut={() => setHover(false)}
            >
                {renderGeometry()}
                <meshStandardMaterial color={color} roughness={0.3} metalness={0.1} />
                <Edges scale={1} threshold={15} color="black" linewidth={2} />
            </mesh>
        </Float>
    )
}

export default function Background3D() {
    const COLORS = {
        RED: "#d93025",
        BLUE: "#0047bb",
        YELLOW: "#f4b400",
        BROWN: "#8b4513",
        BLACK: "#1a1a1a"
    }

    return (
        <div className="canvas-container">
            <Canvas camera={{ position: [0, 0, 15], fov: 45 }}>
                <ambientLight intensity={0.8} />
                <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} />

                {/* 5 Distinct Objects spread across the screen */}

                {/* Left: Red Box */}
                <FloatingShape
                    position={[-12, 0, -2]}
                    rotation={[0.5, 0.5, 0]}
                    scale={2}
                    color={COLORS.RED}
                    type="box"
                />

                {/* Mid-Left: Blue Sphere */}
                <FloatingShape
                    position={[-6, 3, -4]}
                    rotation={[0, 0, 0]}
                    scale={2.2}
                    color={COLORS.BLUE}
                    type="sphere"
                />

                {/* Center: Yellow Icosahedron */}
                <FloatingShape
                    position={[0, -2, 0]}
                    rotation={[0, 0, 0]}
                    scale={2.5}
                    color={COLORS.YELLOW}
                    type="icosahedron"
                />

                {/* Mid-Right: Brown Cone */}
                <FloatingShape
                    position={[6, 2, -3]}
                    rotation={[0.5, 0, -0.5]}
                    scale={2.2}
                    color={COLORS.BROWN}
                    type="cone"
                />

                {/* Right: Black Torus */}
                <FloatingShape
                    position={[12, -1, -2]}
                    rotation={[1, 0.5, 0]}
                    scale={1.8}
                    color={COLORS.BLACK}
                    type="torus"
                />

                <ContactShadows resolution={1024} scale={50} blur={2} opacity={0.2} far={10} color="#000000" />
                <Environment preset="city" />
            </Canvas>
        </div>
    )
}
